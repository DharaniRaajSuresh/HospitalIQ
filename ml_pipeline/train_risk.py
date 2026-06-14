"""
train_risk.py — Trains a RandomForestRegressor to predict pandemic risk score (0-100)
from disease outbreak features. Uses all disease-state combos as training data.
Includes: hyperparameter tuning (GridSearchCV), 5-fold CV, MLflow tracking.
"""

import os, sys, logging
logging.disable(logging.CRITICAL)
os.environ["SKIP_DB_INIT"] = "1"

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, GridSearchCV
from sqlalchemy import func, text

try:
    from ml_utils import setup_mlflow, cross_validate, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR, logger
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import setup_mlflow, cross_validate, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR, logger

from backend.database import SessionLocal
from backend.models import PandemicOutbreak, HospitalBed

MODELS_DIR = MODEL_DIR
os.makedirs(MODELS_DIR, exist_ok=True)

db = SessionLocal()

# Query: aggregate by disease + state across all history
rows = db.query(
    PandemicOutbreak.disease,
    PandemicOutbreak.state,
    func.sum(PandemicOutbreak.confirmed_cases).label("total_confirmed"),
    func.sum(PandemicOutbreak.deaths).label("total_deaths"),
    func.avg(PandemicOutbreak.case_fatality_rate).label("avg_cfr"),
    func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0"),
    func.sum(PandemicOutbreak.bed_demand).label("total_bed_demand"),
    func.sum(PandemicOutbreak.icu_demand).label("total_icu_demand"),
    func.max(PandemicOutbreak.confirmed_cases).label("peak_monthly_cases"),
).group_by(
    PandemicOutbreak.disease, PandemicOutbreak.state
).all()

print(f"Loaded {len(rows)} disease-state combos")

# Get hospital capacity data per state
state_capacity = {}
cap_rows = db.query(
    HospitalBed.state,
    func.sum(HospitalBed.total_beds).label("total_beds"),
    func.avg(HospitalBed.occupancy_rate * 1.0).label("avg_occupancy"),
    func.count(func.distinct(HospitalBed.hospital_name)).label("hospital_count"),
).group_by(HospitalBed.state).all()

for r in cap_rows:
    state_capacity[r.state] = {
        "total_beds": int(r.total_beds or 0),
        "avg_occupancy": float(r.avg_occupancy or 50),
        "hospital_count": int(r.hospital_count or 0),
    }

# Build features + labels
records = []
for r in rows:
    disease = r.disease
    state = r.state
    cap = state_capacity.get(state, {"total_beds": 1000, "avg_occupancy": 50, "hospital_count": 10})

    total_confirmed = int(r.total_confirmed or 0)
    total_deaths = int(r.total_deaths or 0)
    avg_cfr = float(r.avg_cfr or 0)
    avg_r0 = float(r.avg_r0 or 0)
    total_bed_demand = int(r.total_bed_demand or 0)
    total_icu_demand = int(r.total_icu_demand or 0)
    peak_monthly_cases = int(r.peak_monthly_cases or 0)
    total_beds = cap["total_beds"]
    bed_occupancy = cap["avg_occupancy"]
    hospital_count = cap["hospital_count"]

    # Ground truth label: composite of death severity + system overwhelm
    if total_deaths > 0:
        death_sev = min(60, int(np.log10(total_deaths) * 15 - 5))
    else:
        death_sev = 0

    if total_beds > 0 and total_bed_demand > 0:
        ratio = total_bed_demand / max(total_beds, 1)
        overwhelm_sev = min(40, int(np.log10(max(ratio, 1)) * 20))
    else:
        overwhelm_sev = 0

    cfr_bonus = min(15, int(avg_cfr / 5))
    risk_label = min(100, death_sev + overwhelm_sev + cfr_bonus)

    records.append({
        "total_confirmed": total_confirmed,
        "total_deaths": total_deaths,
        "avg_cfr": avg_cfr, "avg_r0": avg_r0,
        "total_bed_demand": total_bed_demand,
        "total_icu_demand": total_icu_demand,
        "peak_monthly_cases": peak_monthly_cases,
        "total_beds": total_beds,
        "bed_occupancy": bed_occupancy,
        "hospital_count": hospital_count,
        "disease": disease, "state": state,
        "risk_label": risk_label,
    })

df = pd.DataFrame(records)
print(f"Generated {len(df)} training records")
print(f"Risk label distribution: min={df['risk_label'].min()}, max={df['risk_label'].max()}, mean={df['risk_label'].mean():.1f}")

# Encode categoricals
disease_encoding = {d: i for i, d in enumerate(sorted(df["disease"].unique()))}
state_encoding = {s: i for i, s in enumerate(sorted(df["state"].unique()))}
df["disease_encoded"] = df["disease"].map(disease_encoding)
df["state_encoded"] = df["state"].map(state_encoding)

feature_cols = [
    "total_confirmed", "total_deaths", "avg_cfr", "avg_r0",
    "total_bed_demand", "total_icu_demand", "peak_monthly_cases",
    "total_beds", "bed_occupancy", "hospital_count",
    "disease_encoded", "state_encoded",
]

X = df[feature_cols].values
y = df["risk_label"].values

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

mlflow = setup_mlflow("risk_scoring")
if mlflow:
    mlflow.start_run(run_name=f"risk_rf_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
    mlflow.log_param("model_type", "RandomForestRegressor")
    mlflow.log_param("feature_count", X.shape[1])
    mlflow.log_param("train_samples", len(X_train))

print("Hyperparameter tuning with GridSearchCV (3-fold)...")
PARAM_GRID = {
    "n_estimators": [100, 200, 300],
    "max_depth": [8, 12, 16],
    "min_samples_leaf": [2, 4, 6],
    "max_features": ["sqrt", "log2"],
}
base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
grid = GridSearchCV(base_model, PARAM_GRID, cv=3, scoring="r2", n_jobs=-1, verbose=0)
grid.fit(X_train_scaled, y_train)

model = grid.best_estimator_
print(f"Best params: {grid.best_params_}")
print(f"Best CV R²: {grid.best_score_:.4f}")

train_score = model.score(X_train_scaled, y_train)
test_score = model.score(X_test_scaled, y_test)
print(f"Train R²: {train_score:.4f}")
print(f"Test R²: {test_score:.4f}")

print("5-fold cross-validation:")
cv_scores = cross_validate(model, X, y, cv=5, scoring="r2")

importances = sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1])
print("\nTop features:")
for name, imp in importances[:8]:
    print(f"  {name}: {imp:.4f}")

# Save artifacts
joblib.dump(model, os.path.join(MODELS_DIR, "risk_model.pkl"))
joblib.dump(scaler, os.path.join(MODELS_DIR, "risk_scaler.pkl"))
joblib.dump({"disease": disease_encoding, "state": state_encoding}, os.path.join(MODELS_DIR, "risk_encoding.pkl"))

metrics = {"train_r2": float(train_score), "test_r2": float(test_score), "cv_r2_mean": float(cv_scores.mean()), "cv_r2_std": float(cv_scores.std())}
params = {"best_params": grid.best_params_, "feature_count": X.shape[1], "train_samples": len(X_train)}
save_model_versioned(model, "risk_model", metrics, params)

if mlflow:
    mlflow.log_metrics(metrics)
    mlflow.log_params(grid.best_params_)
    mlflow.sklearn.log_model(model, "risk_model")
    mlflow.end_run()

print(f"\nSaved: risk_model.pkl, risk_scaler.pkl, risk_encoding.pkl")

# Quick validation
print("\nSample predictions:")
samples = [
    ("COVID-19", "Maharashtra"), ("Ebola", "Maharashtra"), ("H1N1", "Maharashtra"),
    ("SARS", "Maharashtra"), ("Nipah", "Maharashtra"), ("Marburg", "Maharashtra"),
    ("COVID-19", "Delhi"), ("COVID-19", "Kerala"),
]
for disease, state in samples:
    row = df[(df["disease"] == disease) & (df["state"] == state)]
    if len(row) == 0:
        continue
    row = row.iloc[0]
    feats = np.array([[row[c] for c in feature_cols]])
    feats_scaled = scaler.transform(feats)
    pred = float(model.predict(feats_scaled)[0])
    actual = row["risk_label"]
    print(f"  {disease:12s} {state:15s} predicted={pred:.0f} actual={actual}")

db.close()
print("\n✅ Risk model training complete!")
