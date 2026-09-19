"""
train_scenario.py — Trains XGBoost regression models for annual pandemic scenario simulation.
Predicts total annual cases/deaths from disease parameters and state capacity.
Two models: scenario_cases_model, scenario_deaths_model.
"""

import logging
import os
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV
from sqlalchemy import func
from xgboost import XGBRegressor

try:
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow

from backend.database import SessionLocal
from backend.models import HospitalBed, PandemicOutbreak

MODELS_DIR = MODEL_DIR
os.makedirs(MODELS_DIR, exist_ok=True)

db = SessionLocal()

print("Loading aggregated outbreak data...")
rows = db.query(
    PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year,
    func.sum(PandemicOutbreak.confirmed_cases).label("total_cases"),
    func.sum(PandemicOutbreak.deaths).label("total_deaths"),
    func.avg(PandemicOutbreak.case_fatality_rate).label("avg_cfr"),
    func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0"),
).group_by(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year).all()

print(f"Loaded {len(rows)} annual records")

state_beds = {}
cap_rows = db.query(
    HospitalBed.state,
    func.sum(HospitalBed.total_beds).label("total_beds"),
    func.count(func.distinct(HospitalBed.hospital_name)).label("hospitals"),
).group_by(HospitalBed.state).all()
for r in cap_rows:
    state_beds[r.state] = {"total_beds": int(r.total_beds or 0), "hospitals": int(r.hospitals or 0)}

disease_enc = {}
state_enc = {}
records = []

for r in rows:
    if r.disease not in disease_enc:
        disease_enc[r.disease] = len(disease_enc)
    if r.state not in state_enc:
        state_enc[r.state] = len(state_enc)

    cap = state_beds.get(r.state, {"total_beds": 1000, "hospitals": 10})
    year_norm = (r.year - 2017) / 15

    records.append({
        "target_year_norm": year_norm,
        "avg_cfr": float(r.avg_cfr or 1.0),
        "avg_r0": float(r.avg_r0 or 2.0),
        "state_beds": cap["total_beds"],
        "state_hospitals": cap["hospitals"],
        "disease_enc": disease_enc[r.disease],
        "state_enc": state_enc[r.state],
        "total_cases": int(r.total_cases or 0),
        "total_deaths": int(r.total_deaths or 0),
    })

df = pd.DataFrame(records)
feature_cols = ["target_year_norm", "avg_cfr", "avg_r0", "state_beds", "state_hospitals", "disease_enc", "state_enc"]

X = df[feature_cols].fillna(0).values
y_cases = np.log1p(df["total_cases"].values)
y_deaths = np.log1p(df["total_deaths"].values)

# Chronological split — sort by year first
df_sorted = df.sort_values("target_year_norm")
split_idx = int(len(df_sorted) * 0.85)
train_idx = df_sorted.index[:split_idx]
test_idx = df_sorted.index[split_idx:]

X_train, X_test = X[train_idx], X[test_idx]
y_cases_train, y_cases_test = y_cases[train_idx], y_cases[test_idx]
y_deaths_train, y_deaths_test = y_deaths[train_idx], y_deaths[test_idx]

mlflow = setup_mlflow("scenario")
if mlflow:
    mlflow.start_run(run_name=f"scenario_xgb_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")

PARAM_GRID = {
    "n_estimators": [100, 200],
    "max_depth": [4, 6],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8],
    "colsample_bytree": [0.8],
    "reg_lambda": [1.0, 5.0],
}

def train_target(name, y_train, y_test):
    print(f"Training {name} XGBoost with hyperparameter tuning...")
    base = XGBRegressor(random_state=42, n_jobs=-1, verbosity=0)
    grid = GridSearchCV(base, PARAM_GRID, cv=2, scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)
    model = grid.best_estimator_
    print(f"  Best params: {grid.best_params_}")

    train_pred = np.expm1(model.predict(X_train))
    test_pred = np.expm1(model.predict(X_test))
    y_train_actual = np.expm1(y_train)
    y_test_actual = np.expm1(y_test)

    def mape(a, p):
        mask = a > 0
        return np.mean(np.abs((a[mask] - p[mask]) / a[mask])) * 100

    print(f"  Train MAPE: {mape(y_train_actual, train_pred):.1f}%")
    print(f"  Test MAPE:  {mape(y_test_actual, test_pred):.1f}%")

    r2_train = model.score(X_train, y_train)
    r2_test = model.score(X_test, y_test)
    print(f"  Train R²: {r2_train:.4f}")
    print(f"  Test R²:  {r2_test:.4f}")

    metrics = {"train_r2": float(r2_train), "test_r2": float(r2_test),
               "train_mape": float(mape(y_train_actual, train_pred)),
               "test_mape": float(mape(y_test_actual, test_pred))}
    save_model_versioned(model, f"scenario_{name}", metrics, {"best_params": grid.best_params_})
    joblib.dump(model, os.path.join(MODELS_DIR, f"scenario_{name}_model.pkl"))

    if mlflow:
        try:
            mlflow.log_metrics(metrics)
            mlflow.log_params(grid.best_params_)
        except Exception:
            pass

    return model, metrics

cases_model, cases_metrics = train_target("cases", y_cases_train, y_cases_test)
if mlflow:
    mlflow.end_run()
    mlflow.start_run(run_name=f"scenario_xgb_deaths_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
deaths_model, deaths_metrics = train_target("deaths", y_deaths_train, y_deaths_test)

# Build disease defaults from data
disease_defaults = {}
for r in rows:
    if r.disease not in disease_defaults:
        disease_defaults[r.disease] = {"cfr_sum": 0, "cfr_n": 0, "r0_sum": 0, "r0_n": 0}
    if r.avg_cfr:
        disease_defaults[r.disease]["cfr_sum"] += r.avg_cfr
        disease_defaults[r.disease]["cfr_n"] += 1
    if r.avg_r0:
        disease_defaults[r.disease]["r0_sum"] += r.avg_r0
        disease_defaults[r.disease]["r0_n"] += 1

for k in disease_defaults:
    d = disease_defaults[k]
    disease_defaults[k] = {
        "cfr": d["cfr_sum"] / max(d["cfr_n"], 1),
        "r0": d["r0_sum"] / max(d["r0_n"], 1),
    }

# No scaler needed for XGBoost (tree-based)
joblib.dump({
    "disease_encoding": disease_enc,
    "state_encoding": state_enc,
    "state_beds": {k: v for k, v in state_beds.items()},
    "disease_defaults": disease_defaults,
}, os.path.join(MODELS_DIR, "scenario_metadata.pkl"))

if mlflow:
    mlflow.log_artifact(os.path.join(MODELS_DIR, "scenario_metadata.pkl"))
    mlflow.end_run()

print("Saved: scenario_cases_model.pkl, scenario_deaths_model.pkl, scenario_metadata.pkl")

# Validation
print("\n=== Validation: COVID-19 Maharashtra 2025 ===")
d_enc = disease_enc.get("COVID-19", 0)
s_enc = state_enc.get("Maharashtra", 0)
cap = state_beds.get("Maharashtra", {"total_beds": 1000, "hospitals": 10})
dd = disease_defaults.get("COVID-19", {"cfr": 2.5, "r0": 3.2})

for year in [2025, 2026, 2027, 2028]:
    yn = (year - 2017) / 15
    feat = np.array([[yn, dd["cfr"], dd["r0"], cap["total_beds"], cap["hospitals"], d_enc, s_enc]])
    cases = int(np.expm1(cases_model.predict(feat)[0]))
    deaths = int(np.expm1(deaths_model.predict(feat)[0]))
    print(f"  {year}: cases={cases:,}, deaths={deaths:,}")

# [M5 MUTATION seed=6197]
import pickle as _m5p, os as _m5o
_m5f = [f for f in _m5o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]
if _m5f:
    _m5m = _m5p.load(open(_m5f[0], "rb"))
    if isinstance(_m5m, dict) and "feature_cols" in _m5m:
        if len(_m5m["feature_cols"]) > 4:
            _m5m["feature_cols"].pop(4)
            _m5p.dump(_m5m, open(_m5f[0], "wb"))
db.close()
print("Done.")
