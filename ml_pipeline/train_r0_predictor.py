"""
train_r0_predictor.py — Trains XGBoost for Reproduction Rate (R0) prediction.
Features: population_density, vaccination_rate, mutation_factor,
          years_since_2020, year_norm, disease_enc, state_enc.
Synthetic data teaches: R0 decays with time/vaccination, spikes with mutation.
"""
import logging
import math
import os
import random
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

from collections import defaultdict

import joblib
import numpy as np
import pandas as pd
from sqlalchemy import func
from xgboost import XGBRegressor

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow

from backend.database import SessionLocal
from backend.models import PandemicOutbreak

STATE_POP_MILLIONS = {
    "Uttar Pradesh": 241.1, "Maharashtra": 127.5, "Bihar": 128.6,
    "West Bengal": 99.6, "Madhya Pradesh": 87.6, "Rajasthan": 81.9,
    "Tamil Nadu": 77.1, "Gujarat": 72.4, "Karnataka": 68.1,
    "Andhra Pradesh": 53.3, "Odisha": 46.6, "Telangana": 38.3,
    "Jharkhand": 39.9, "Assam": 36.5, "Kerala": 35.9,
    "Punjab": 30.9, "Haryana": 30.6, "Chhattisgarh": 30.2,
    "Delhi": 22.3, "Jammu and Kashmir": 13.6, "Uttarakhand": 11.9,
    "Himachal Pradesh": 7.5, "Tripura": 4.1, "Meghalaya": 3.4,
    "Manipur": 3.3, "Nagaland": 2.2, "Goa": 1.6,
    "Arunachal Pradesh": 1.6, "Mizoram": 1.2, "Sikkim": 0.7,
}
try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from seed_pandemic import STATE_DISTRICTS
except ImportError:
    from districts import STATE_DISTRICTS

DISEASE_BASELINE_R0 = {
    "COVID-19": 2.5, "Ebola": 1.8, "H1N1": 1.5,
    "SARS": 3.0, "Nipah": 1.8, "Marburg": 1.7,
}

MODELS_DIR = MODEL_DIR
os.makedirs(MODELS_DIR, exist_ok=True)
db = SessionLocal()

print("Loading aggregated outbreak data...")
rows = db.query(
    PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year,
    func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0"),
).group_by(
    PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year
).order_by(
    PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year
).all()
print(f"Loaded {len(rows)} annual records")

disease_enc = {}
state_enc = {}
state_district_count = {}
for st, dists in STATE_DISTRICTS.items():
    state_district_count[st] = len(dists)
if not state_district_count:
    state_district_count = {s: 10 for s in STATE_POP_MILLIONS}

grouped = defaultdict(list)
for r in rows:
    grouped[(r.disease, r.state)].append(r)

rng = random.Random(42)

# ---- STEP 1: Real-data records (with mutation_factor from YoY R0 change) ----
records = []
for (disease, state), yearly_records in grouped.items():
    prev_r0 = None
    for r in yearly_records:
        disease_enc.setdefault(r.disease, len(disease_enc))
        state_enc.setdefault(r.state, len(state_enc))
        population_m = STATE_POP_MILLIONS.get(r.state, 10)
        nd = state_district_count.get(r.state, 10)
        population_density = (population_m * 1_000_000) / max(nd, 1)
        yrs = max(0, r.year - 2020)
        vacc = 1.0 / (1.0 + math.exp(-0.45 * (yrs - 4)))
        yr_norm = (r.year - 2017) / 20.0
        current_r0 = float(r.avg_r0 or 2.0)

        if prev_r0 is not None and prev_r0 > 0:
            yoy = current_r0 / prev_r0
            expected_decay = 0.93
            mut = yoy / expected_decay
            mut = max(0.5, min(3.0, round(mut, 4)))
        else:
            mut = 1.0
        prev_r0 = current_r0

        records.append({
            "population_density": population_density,
            "vaccination_rate": round(vacc, 4),
            "mutation_factor": mut,
            "years_since_2020": yrs,
            "year_norm": yr_norm,
            "disease_enc": disease_enc[r.disease],
            "state_enc": state_enc[r.state],
            "target_r0": current_r0,
        })

# ---- STEP 2: Synthetic data ----
# NOTE: Target R0 is computed from features via a formula (baseline*decay*vacc*...).
# The model learns to reverse-engineer this formula rather than predict real R0 dynamics.
# R² ~0.99 reflects formula-reconstruction accuracy, not real-world predictive skill.
# Vaccination_rate is a deterministic sigmoid of years_since_2020 (no real vaccination data).
# R0 = baseline * 0.96^yrs * (1 - 0.4*vacc) * (1 + 0.3*(mut-1)) * density_mod
print("Generating synthetic data...")
aug_records = []

for (disease, state), yearly_records in grouped.items():
    population_m = STATE_POP_MILLIONS.get(state, 10)
    nd = state_district_count.get(state, 10)
    pop_density = (population_m * 1_000_000) / max(nd, 1)
    density_mod = 1.0 + 0.08 * (population_m / 100.0)
    d_enc = disease_enc[disease]
    s_enc = state_enc[state]
    baseline = DISEASE_BASELINE_R0.get(disease, 2.0)

    # Scenario cycles: different mutation periods + random perturbations
    for scenario_idx in range(4):
        mut_cycle_start = rng.choice([2020, 2023, 2027, 2030, 2035])
        mut_cycle_end = mut_cycle_start + rng.randint(1, 3)
        mut_peak = rng.choice([1.3, 1.5, 1.8, 2.0])

        for year in range(2020, 2041):
            yrs = max(0, year - 2020)
            vacc = 1.0 / (1.0 + math.exp(-0.45 * (yrs - 4)))
            yr_norm = (year - 2017) / 20.0
            decay = 0.96 ** yrs

            # Mutation ramps up and down
            if mut_cycle_start <= year <= mut_cycle_end:
                mid = (mut_cycle_start + mut_cycle_end) / 2.0
                dist_from_mid = abs(year - mid) / max(1, (mut_cycle_end - mut_cycle_start) / 2.0)
                mut = 1.0 + (mut_peak - 1.0) * max(0, 1.0 - dist_from_mid)
            else:
                mut = 1.0

            vacc_effect = 1.0 - 0.40 * vacc
            mut_effect = 1.0 + 0.30 * (mut - 1.0)
            target = baseline * decay * vacc_effect * mut_effect * density_mod
            target = max(0.3, min(6.0, round(target, 4)))

            aug_records.append({
                "population_density": pop_density,
                "vaccination_rate": round(vacc, 4),
                "mutation_factor": round(mut, 4),
                "years_since_2020": yrs,
                "year_norm": yr_norm,
                "disease_enc": d_enc,
                "state_enc": s_enc,
                "target_r0": target,
            })

# Add cross-section data with explicit mutation_factor grid
for (disease, state), yearly_records in grouped.items():
    population_m = STATE_POP_MILLIONS.get(state, 10)
    nd = state_district_count.get(state, 10)
    pop_density = (population_m * 1_000_000) / max(nd, 1)
    d_enc = disease_enc[disease]
    s_enc = state_enc[state]
    baseline = DISEASE_BASELINE_R0.get(disease, 2.0)
    for yrs in range(0, 21):
        yr_norm = (2020 + yrs - 2017) / 20.0
        vacc = 1.0 / (1.0 + math.exp(-0.45 * (yrs - 4)))
        for mut in [0.5, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5]:
            decay = 0.96 ** yrs
            ve = 1.0 - 0.40 * vacc
            me = 1.0 + 0.30 * (mut - 1.0)
            target = baseline * decay * ve * me
            target = max(0.3, min(6.0, round(target, 4)))
            aug_records.append({
                "population_density": pop_density,
                "vaccination_rate": round(vacc, 4),
                "mutation_factor": mut,
                "years_since_2020": yrs,
                "year_norm": yr_norm,
                "disease_enc": d_enc,
                "state_enc": s_enc,
                "target_r0": target,
            })

feature_cols = [
    "population_density", "vaccination_rate", "mutation_factor",
    "years_since_2020", "year_norm", "disease_enc", "state_enc",
]

df_real = pd.DataFrame(records)
df_aug = pd.DataFrame(aug_records)
print(f"Real: {len(df_real)}, Augmented: {len(df_aug)}")

df_aug = df_aug[feature_cols + ["target_r0"]]
df_real = df_real[feature_cols + ["target_r0"]]

sampled_aug = df_aug.sample(n=int(len(df_aug) * 0.5), random_state=42).reset_index(drop=True)
print(f"Sampled augmented: {len(sampled_aug)}")

df = pd.concat([df_real, sampled_aug], ignore_index=True)
print(f"Total: {len(df)}")

X = df[feature_cols].fillna(0).values
y = df["target_r0"].values

from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
print(f"Train: {len(X_train)}, Test: {len(X_test)}")

mlflow = setup_mlflow("r0_predictor")
if mlflow:
    mlflow.start_run(run_name=f"r0_xgb_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")

model = XGBRegressor(
    n_estimators=600, max_depth=8, learning_rate=0.05,
    subsample=0.85, colsample_bytree=0.8,
    reg_lambda=2.0, reg_alpha=0.5,
    random_state=42, n_jobs=-1, verbosity=0,
)

print("Training XGBoost R0 predictor...")
model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

def mape(a, p):
    mask = a > 0
    return np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100

train_pred = model.predict(X_train)
test_pred = model.predict(X_test)
r2_train = model.score(X_train, y_train)
r2_test = model.score(X_test, y_test)
print(f"\nTrain R2: {r2_train:.4f}, Train MAPE: {mape(y_train, train_pred):.1f}%")
print(f"Test  R2: {r2_test:.4f}, Test  MAPE: {mape(y_test, test_pred):.1f}%")

importances = model.feature_importances_
print("\nFeature importances:")
for name, imp in sorted(zip(feature_cols, importances), key=lambda x: -x[1]):
    print(f"  {name}: {imp:.4f}")

metrics = {"train_r2": float(r2_train), "test_r2": float(r2_test),
           "train_mape": float(mape(y_train, train_pred)),
           "test_mape": float(mape(y_test, test_pred))}
params = {"n_estimators": 600, "max_depth": 8, "learning_rate": 0.05}

save_model_versioned(model, "r0_model", metrics, params)
joblib.dump(model, os.path.join(MODELS_DIR, "r0_model.pkl"))

from backend.app_state import normalize_state

metadata = {
    "disease_encoding": dict(disease_enc),
    "state_encoding": {normalize_state(s): v for s, v in state_enc.items()},
    "state_population_density": {},
    "feature_names": feature_cols,
    "disease_defaults": {},
}
for state in state_enc:
    pop_m = STATE_POP_MILLIONS.get(state, 10)
    nd = state_district_count.get(state, 10)
    metadata["state_population_density"][normalize_state(state)] = (pop_m * 1_000_000) / max(nd, 1)
for d in disease_enc:
    sub = df_real[df_real["disease_enc"] == disease_enc[d]]
    avg_r0 = float(sub["target_r0"].mean()) if len(sub) > 0 else DISEASE_BASELINE_R0.get(d, 2.0)
    yrs_avg = 5
    vacc_default = 1.0 / (1.0 + math.exp(-0.45 * (yrs_avg - 4)))
    metadata["disease_defaults"][normalize_state(d)] = {
        "avg_r0": round(avg_r0, 3),
        "vaccination_rate": round(vacc_default, 3),
    }

joblib.dump(metadata, os.path.join(MODELS_DIR, "r0_metadata.pkl"))
print("\nSaved: r0_model.pkl, r0_metadata.pkl")

if mlflow:
    mlflow.log_metrics(metrics)
    mlflow.log_params(params)
    mlflow.end_run()

# Validation
print("\n=== Yearly decay: COVID-19 Maharashtra (2025-2035) ===")
d_enc = disease_enc.get("COVID-19", 0)
s_enc = state_enc.get("Maharashtra", 0)
pop_density = metadata["state_population_density"].get("Maharashtra", 100_000)

for year in range(2025, 2036):
    yrs = max(0, year - 2020)
    vacc = 1.0 / (1.0 + math.exp(-0.45 * (yrs - 4)))
    yr_norm = (year - 2017) / 20.0
    for mut_label, mut_val in [("normal", 1.0), ("variant", 1.5)]:
        feat = np.array([[pop_density, vacc, mut_val, yrs, yr_norm, d_enc, s_enc]])
        pred = float(model.predict(feat)[0])
        pred = max(0.3, min(6.0, round(pred, 3)))
        if mut_label == "normal":
            marker = ""
            ref = pred
        else:
            marker = f" (variant: +{round(pred - ref, 3)})"
        if mut_label == "variant":
            print(f"  {year}: normal={ref:.3f}, variant={pred:.3f}{marker}  (vacc={vacc:.3f})")

# Mutation sensitivity
print("\n=== Mutation sensitivity: COVID-19 Maharashtra 2027 ===")
for mut in [0.5, 0.8, 1.0, 1.3, 1.6, 2.0, 2.5]:
    feat = np.array([[pop_density, 0.794, mut, 7, 0.5, d_enc, s_enc]])
    pred = float(model.predict(feat)[0])
    print(f"  mut={mut:.1f}: R0 = {max(0.3, min(6.0, round(pred, 3))):.3f}")

# Vaccination sensitivity
print("\n=== Vaccination sensitivity: COVID-19 Maharashtra 2030 ===")
for vacc in [0.0, 0.2, 0.4, 0.6, 0.8, 0.95]:
    feat = np.array([[pop_density, vacc, 1.0, 10, 0.65, d_enc, s_enc]])
    pred = float(model.predict(feat)[0])
    print(f"  vacc={vacc:.2f}: R0 = {max(0.3, min(6.0, round(pred, 3))):.3f}")

# Disease comparison
print("\n=== Disease comparison: Maharashtra 2027 ===")
for disease in ["COVID-19", "Ebola", "H1N1", "SARS", "Nipah", "Marburg"]:
    de = disease_enc.get(disease, 0)
    feat = np.array([[pop_density, 0.794, 1.0, 7, 0.5, de, s_enc]])
    pred = float(model.predict(feat)[0])
    print(f"  {disease}: R0 = {max(0.3, min(6.0, round(pred, 3))):.3f}")

db.close()
print("\nDone.")
