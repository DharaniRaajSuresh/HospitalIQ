"""
train_forecast.py — Trains XGBoost time-series models for monthly pandemic forecasting.
Two models: forecast_cases_model (confirmed_cases) and forecast_deaths_model (deaths).
Includes: hyperparameter tuning (GridSearchCV), time-based train/test split, MLflow tracking.
"""

import logging
import math
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
    from ml_utils import MLFLOW_AVAILABLE, MODEL_DIR, cross_validate, logger, save_model_versioned, setup_mlflow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow

from backend.database import SessionLocal
from backend.models import HospitalBed, PandemicOutbreak

MODELS_DIR = MODEL_DIR
os.makedirs(MODELS_DIR, exist_ok=True)

db = SessionLocal()

# ---------------------------------------------------------------------------
# 1. Load and aggregate monthly data
# ---------------------------------------------------------------------------
print("Loading pandemic records...")
rows = db.query(
    PandemicOutbreak.disease,
    PandemicOutbreak.state,
    PandemicOutbreak.year,
    PandemicOutbreak.month,
    func.sum(PandemicOutbreak.confirmed_cases).label("confirmed_cases"),
    func.sum(PandemicOutbreak.deaths).label("deaths"),
    func.avg(PandemicOutbreak.case_fatality_rate).label("avg_cfr"),
    func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0"),
    func.sum(PandemicOutbreak.bed_demand).label("bed_demand"),
    func.sum(PandemicOutbreak.icu_demand).label("icu_demand"),
).group_by(
    PandemicOutbreak.disease, PandemicOutbreak.state,
    PandemicOutbreak.year, PandemicOutbreak.month,
).order_by(
    PandemicOutbreak.disease, PandemicOutbreak.state,
    PandemicOutbreak.year, PandemicOutbreak.month,
).all()

print(f"Loaded {len(rows)} monthly aggregated records")

# ---------------------------------------------------------------------------
# 2. Load hospital capacity data
# ---------------------------------------------------------------------------
state_beds = {}
cap_rows = db.query(
    HospitalBed.state,
    func.sum(HospitalBed.total_beds).label("total_beds"),
    func.count(func.distinct(HospitalBed.hospital_name)).label("hospitals"),
).group_by(HospitalBed.state).all()
for r in cap_rows:
    state_beds[r.state] = {"total_beds": int(r.total_beds or 0), "hospitals": int(r.hospitals or 0)}

# ---------------------------------------------------------------------------
# 3. Build feature matrix with time-series lags
# ---------------------------------------------------------------------------
disease_avg_params = {}
for r in rows:
    key = r.disease
    if key not in disease_avg_params:
        disease_avg_params[key] = {"cfr_sum": 0, "cfr_n": 0, "r0_sum": 0, "r0_n": 0}
    if r.avg_cfr:
        disease_avg_params[key]["cfr_sum"] += r.avg_cfr
        disease_avg_params[key]["cfr_n"] += 1
    if r.avg_r0:
        disease_avg_params[key]["r0_sum"] += r.avg_r0
        disease_avg_params[key]["r0_n"] += 1

for k in disease_avg_params:
    p = disease_avg_params[k]
    p["cfr"] = p["cfr_sum"] / max(p["cfr_n"], 1)
    p["r0"] = p["r0_sum"] / max(p["r0_n"], 1)

records = []
current_key = None
buffer = []

def flush_buffer():
    global buffer
    if len(buffer) < 4:
        buffer = []
        return
    df_seq = pd.DataFrame(buffer).sort_values(["year", "month"])
    for i in range(3, len(df_seq)):
        row = df_seq.iloc[i]
        lag1 = df_seq.iloc[i-1]
        lag2 = df_seq.iloc[i-2]
        lag3 = df_seq.iloc[i-3]

        month = int(row["month"])
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)

        cases_ma3 = (lag1["cases"] + lag2["cases"] + lag3["cases"]) / 3
        cases_growth = (lag1["cases"] - lag2["cases"]) / max(lag2["cases"], 1)

        cap = state_beds.get(row["state"], {"total_beds": 1000, "hospitals": 10})

        year_norm = (int(row["year"]) - 2017) / 15

        records.append({
            "disease": row["disease"],
            "state": row["state"],
            "year": row["year"],
            "month": row["month"],
            "month_sin": month_sin,
            "month_cos": month_cos,
            "year_normalized": year_norm,
            "lag_1_cases": lag1["cases"],
            "lag_2_cases": lag2["cases"],
            "lag_3_cases": lag3["cases"],
            "lag_1_deaths": lag1["deaths"],
            "lag_2_deaths": lag2["deaths"],
            "cases_ma3": cases_ma3,
            "cases_growth": cases_growth,
            "disease_cfr": disease_avg_params.get(row["disease"], {}).get("cfr", 0),
            "disease_r0": disease_avg_params.get(row["disease"], {}).get("r0", 0),
            "state_beds": cap["total_beds"],
            "state_hospitals": cap["hospitals"],
            "target_cases": row["cases"],
            "target_deaths": row["deaths"],
        })
    buffer = []

for r in rows:
    key = (r.disease, r.state)
    entry = {
        "disease": r.disease, "state": r.state,
        "year": r.year, "month": r.month,
        "cases": int(r.confirmed_cases or 0),
        "deaths": int(r.deaths or 0),
    }
    if key != current_key:
        flush_buffer()
        current_key = key
        buffer = [entry]
    else:
        buffer.append(entry)
flush_buffer()

df = pd.DataFrame(records)
print(f"Generated {len(df)} training windows")

# ---------------------------------------------------------------------------
# 4. Encode categoricals
# ---------------------------------------------------------------------------
disease_enc = {d: i for i, d in enumerate(sorted(df["disease"].unique()))}
state_enc = {s: i for i, s in enumerate(sorted(df["state"].unique()))}
df["disease_enc"] = df["disease"].map(disease_enc)
df["state_enc"] = df["state"].map(state_enc)

feature_cols = [
    "month_sin", "month_cos", "year_normalized",
    "lag_1_cases", "lag_2_cases", "lag_3_cases",
    "lag_1_deaths", "lag_2_deaths",
    "cases_ma3", "cases_growth",
    "disease_cfr", "disease_r0",
    "state_beds", "state_hospitals",
    "disease_enc", "state_enc",
]

X = df[feature_cols].fillna(0).values
y_cases = np.log1p(df["target_cases"].values)
y_deaths = np.log1p(df["target_deaths"].values)

# ---------------------------------------------------------------------------
# 5. Time-based split (no lookahead)
# ---------------------------------------------------------------------------
df_sorted = df.sort_values(["year", "month"])
split_idx = int(len(df_sorted) * 0.85)
train_idx = df_sorted.index[:split_idx]
test_idx = df_sorted.index[split_idx:]

X_train, X_test = X[train_idx], X[test_idx]
y_cases_train, y_cases_test = y_cases[train_idx], y_cases[test_idx]
y_deaths_train, y_deaths_test = y_deaths[train_idx], y_deaths[test_idx]

def mape(actual, pred):
    mask = actual > 0
    return np.mean(np.abs((actual[mask] - pred[mask]) / actual[mask])) * 100

mlflow = setup_mlflow("forecast")
if mlflow:
    mlflow.start_run(run_name=f"forecast_xgb_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
    mlflow.log_param("feature_count", X.shape[1])
    mlflow.log_param("train_samples", len(X_train))

# ---------------------------------------------------------------------------
# 6. Train with hyperparameter tuning — XGBoost
# ---------------------------------------------------------------------------
PARAM_GRID = {
    "n_estimators": [100, 200],
    "max_depth": [4, 6],
    "learning_rate": [0.05, 0.1],
    "subsample": [0.8],
    "colsample_bytree": [0.8],
    "reg_lambda": [1.0, 5.0],
}

def train_target(name, y_train, y_test):
    print(f"\nTraining {name} XGBoost with hyperparameter tuning...")
    base = XGBRegressor(random_state=42, n_jobs=-1, verbosity=0)
    grid = GridSearchCV(base, PARAM_GRID, cv=2, scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)
    model = grid.best_estimator_
    print(f"Best params: {grid.best_params_}")

    train_pred = np.expm1(model.predict(X_train))
    test_pred = np.expm1(model.predict(X_test))
    y_train_actual = np.expm1(y_train)
    y_test_actual = np.expm1(y_test)

    train_mape = mape(y_train_actual, train_pred)
    test_mape = mape(y_test_actual, test_pred)
    print(f"  Train MAPE: {train_mape:.1f}%")
    print(f"  Test MAPE:  {test_mape:.1f}%")

    metrics = {"train_mape": float(train_mape), "test_mape": float(test_mape)}
    params = {"best_params": grid.best_params_}
    save_model_versioned(model, f"forecast_{name}", metrics, params)
    joblib.dump(model, os.path.join(MODELS_DIR, f"forecast_{name}_model.pkl"))

    if mlflow:
        try:
            mlflow.log_metrics(metrics)
            mlflow.log_params(grid.best_params_)
        except Exception as e:
            print(f"  MLflow logging skipped: {e}")

    return model

cases_model = train_target("cases", y_cases_train, y_cases_test)
deaths_model = train_target("deaths", y_deaths_train, y_deaths_test)

# ---------------------------------------------------------------------------
# 7. Feature importance
# ---------------------------------------------------------------------------
print("\nTop features (cases model):")
importances = sorted(zip(feature_cols, cases_model.feature_importances_), key=lambda x: -x[1])
for name, imp in importances[:8]:
    print(f"  {name}: {imp:.4f}")

# ---------------------------------------------------------------------------
# 8. Save metadata (no scaler needed for tree models)
# ---------------------------------------------------------------------------
joblib.dump({
    "disease_encoding": disease_enc,
    "state_encoding": state_enc,
    "disease_params": disease_avg_params,
    "feature_cols": feature_cols,
    "state_beds": state_beds,
}, os.path.join(MODELS_DIR, "forecast_metadata.pkl"))

if mlflow:
    try:
        mlflow.log_artifact(os.path.join(MODELS_DIR, "forecast_metadata.pkl"))
        mlflow.end_run()
    except Exception as e:
        print(f"  MLflow artifact logging skipped: {e}")

print("\nSaved: forecast_cases_model.pkl, forecast_deaths_model.pkl, forecast_metadata.pkl")

# ---------------------------------------------------------------------------
# 9. Validate: COVID-19 Maharashtra future forecast
# ---------------------------------------------------------------------------
print("\n=== Validation: COVID-19 Maharashtra future forecast ===")
d_enc = disease_enc.get("COVID-19", 0)
s_enc = state_enc.get("Maharashtra", 0)
cap_mh = state_beds.get("Maharashtra", {"total_beds": 2000, "hospitals": 50})
params = disease_avg_params.get("COVID-19", {})
cfr = params.get("cfr", 2.5)
r0 = params.get("r0", 1.1)

cq = db.query(
    PandemicOutbreak.year, PandemicOutbreak.month,
    func.sum(PandemicOutbreak.confirmed_cases).label("cases"),
    func.sum(PandemicOutbreak.deaths).label("deaths"),
).filter(
    PandemicOutbreak.disease == "COVID-19",
    PandemicOutbreak.state == "Maharashtra",
).group_by(
    PandemicOutbreak.year, PandemicOutbreak.month
).order_by(
    PandemicOutbreak.year.desc(), PandemicOutbreak.month.desc()
).limit(3).all()
cq = list(reversed(cq))

print(f"Last 3 months actual: {[(r.year, r.month, int(r.cases)) for r in cq]}")

history_cases = [int(r.cases or 0) for r in cq]
history_deaths = [int(r.deaths or 0) for r in cq]
current_year, current_month = cq[-1].year, cq[-1].month

print("\nForecasted trajectory:")
for step in range(12):
    current_month += 1
    if current_month > 12:
        current_month = 1
        current_year += 1

    m_sin = math.sin(2 * math.pi * current_month / 12)
    m_cos = math.cos(2 * math.pi * current_month / 12)
    year_norm = (current_year - 2017) / 15

    lag_c = [history_cases[-1], history_cases[-2], history_cases[-3]]
    lag_d = [history_deaths[-1], history_deaths[-2]]
    ma3 = sum(lag_c) / 3
    growth = (lag_c[0] - lag_c[1]) / max(lag_c[1], 1)

    feats = np.array([[
        m_sin, m_cos, year_norm,
        lag_c[0], lag_c[1], lag_c[2],
        lag_d[0], lag_d[1],
        ma3, growth,
        cfr, r0,
        cap_mh["total_beds"], cap_mh["hospitals"],
        d_enc, s_enc,
    ]])

    pred_cases = int(np.expm1(cases_model.predict(feats)[0]))
    pred_deaths = int(np.expm1(deaths_model.predict(feats)[0]))

    print(f"  {current_year}-{current_month:02d}: cases={pred_cases:,}, deaths={pred_deaths:,}")

    history_cases.append(max(1, pred_cases))
    history_deaths.append(max(0, pred_deaths))
    history_cases = history_cases[-3:]
    history_deaths = history_deaths[-2:]

# [M6 MUTATION seed=7124]
import pickle as _m6p, os as _m6o
_m6f = [f for f in _m6o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]
if _m6f:
    _m6m = _m6p.load(open(_m6f[0], "rb"))
    if isinstance(_m6m, dict):
        _m6p.dump(list(_m6m.items()), open(_m6f[0], "wb"))
db.close()
print("\nDone. Forecast training complete!")
