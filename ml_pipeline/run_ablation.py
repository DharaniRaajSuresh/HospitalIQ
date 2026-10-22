"""
run_ablation.py — Ablation studies for all ML models.
Removes one feature group at a time and reports MAPE/R² impact.
"""

import logging
import os
import sys
import warnings
logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import numpy as np
import pandas as pd
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from xgboost import XGBRegressor
from sqlalchemy import func

from ml_utils import MODEL_DIR, save_model_versioned
from evaluation_config import DEFAULT_PARAM_GRID_XGB
from backend.database import SessionLocal
from backend.models import HospitalBed, PandemicOutbreak

from baseline_models import mape

db = SessionLocal()


def run_forecast_ablation():
    print("\n" + "=" * 60)
    print("ABLATION STUDY: Forecast Predictor")
    print("=" * 60)

    rows = db.query(
        PandemicOutbreak.disease, PandemicOutbreak.state,
        PandemicOutbreak.year, PandemicOutbreak.month,
        func.sum(PandemicOutbreak.confirmed_cases).label("confirmed_cases"),
        func.sum(PandemicOutbreak.deaths).label("deaths"),
    ).group_by(
        PandemicOutbreak.disease, PandemicOutbreak.state,
        PandemicOutbreak.year, PandemicOutbreak.month,
    ).order_by(
        PandemicOutbreak.disease, PandemicOutbreak.state,
        PandemicOutbreak.year, PandemicOutbreak.month,
    ).all()

    # Build feature matrix (simplified — same as train_forecast)
    records = []
    current_key = None
    buffer = []

    def flush_buffer():
        if len(buffer) < 4:
            return
        df_seq = pd.DataFrame(buffer).sort_values(["year", "month"])
        for i in range(3, len(df_seq)):
            row = df_seq.iloc[i]
            lag1, lag2, lag3 = df_seq.iloc[i-1], df_seq.iloc[i-2], df_seq.iloc[i-3]
            records.append({
                "lag_1_cases": lag1["cases"], "lag_2_cases": lag2["cases"],
                "lag_3_cases": lag3["cases"], "lag_1_deaths": lag1["deaths"],
                "lag_2_deaths": lag2["deaths"],
                "month_sin": np.sin(2 * np.pi * row["month"] / 12),
                "month_cos": np.cos(2 * np.pi * row["month"] / 12),
                "cases_ma3": (lag1["cases"] + lag2["cases"] + lag3["cases"]) / 3,
                "cases_growth": (lag1["cases"] - lag2["cases"]) / max(lag2["cases"], 1),
                "target_cases": row["cases"],
            })

    for r in rows:
        key = (r.disease, r.state)
        entry = {"disease": r.disease, "state": r.state, "year": r.year,
                 "month": r.month, "cases": int(r.confirmed_cases or 0),
                 "deaths": int(r.deaths or 0)}
        if key != current_key:
            flush_buffer()
            current_key = key
            buffer = [entry]
        else:
            buffer.append(entry)
    flush_buffer()

    df = pd.DataFrame(records)
    if df.empty:
        print("  No forecast data available")
        return

    # Feature groups for ablation
    feature_groups = {
        "lag_features": ["lag_1_cases", "lag_2_cases", "lag_3_cases", "lag_1_deaths", "lag_2_deaths"],
        "seasonal": ["month_sin", "month_cos"],
        "trend_features": ["cases_ma3", "cases_growth"],
    }
    all_features = []
    for v in feature_groups.values():
        all_features.extend(v)

    # Full model performance
    X = df[all_features].fillna(0).values
    y = np.log1p(df["target_cases"].values)
    split = int(len(X) * 0.85)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    base = XGBRegressor(random_state=42, n_jobs=-1, verbosity=0)
    grid = GridSearchCV(base, DEFAULT_PARAM_GRID_XGB, cv=TimeSeriesSplit(n_splits=3),
                        scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)
    full_model = XGBRegressor(**grid.best_params_, random_state=42, n_jobs=-1, verbosity=0)
    full_model.fit(X_train, y_train)
    full_pred = np.expm1(full_model.predict(X_test))
    y_test_actual = np.expm1(y_test)
    full_mape = mape(y_test_actual, full_pred)
    print(f"\nFull model test MAPE: {full_mape:.2f}%")

    # Ablate each group
    results = []
    for group_name, features in feature_groups.items():
        remaining = [f for f in all_features if f not in features]
        X_abl = df[remaining].fillna(0).values
        X_tr, X_te = X_abl[:split], X_abl[split:]

        model = XGBRegressor(n_estimators=200, max_depth=4, random_state=42, n_jobs=-1, verbosity=0)
        model.fit(X_tr, y_train)
        pred = np.expm1(model.predict(X_te))
        abl_mape = mape(y_test_actual, pred)
        delta = abl_mape - full_mape
        results.append({"Group Removed": group_name, "MAPE": f"{abl_mape:.2f}%",
                        "Δ vs Full": f"{delta:+.2f}%"})
        print(f"  Without {group_name}: MAPE = {abl_mape:.2f}% (Δ = {delta:+.2f}%)")

    return pd.DataFrame(results)


def run_scenario_ablation():
    print("\n" + "=" * 60)
    print("ABLATION STUDY: Scenario Predictor")
    print("=" * 60)

    rows = db.query(
        PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year,
        func.sum(PandemicOutbreak.confirmed_cases).label("total_cases"),
        func.sum(PandemicOutbreak.deaths).label("total_deaths"),
    ).group_by(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year).all()

    if not rows:
        print("  No scenario data available")
        return

    feature_groups = {
        "disease_params": ["disease_enc"],
        "state_capacity": ["state_beds"],
        "year_trend": ["target_year_norm"],
    }
    all_features = ["target_year_norm", "state_beds", "disease_enc"]

    df = pd.DataFrame([{
        "target_year_norm": (r.year - 2017) / 15,
        "state_beds": 1000,
        "disease_enc": hash(r.disease) % 10,
        "total_cases": int(r.total_cases or 0),
    } for r in rows])

    X = df[all_features].fillna(0).values
    y = np.log1p(df["total_cases"].values)
    split = int(len(X) * 0.85)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    base = XGBRegressor(random_state=42, n_jobs=-1, verbosity=0)
    grid = GridSearchCV(base, DEFAULT_PARAM_GRID_XGB, cv=TimeSeriesSplit(n_splits=3),
                        scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)
    full_model = XGBRegressor(**grid.best_params_, random_state=42, n_jobs=-1, verbosity=0)
    full_model.fit(X_train, y_train)
    full_pred = np.expm1(full_model.predict(X_test))
    y_test_actual = np.expm1(y_test)
    full_mape = mape(y_test_actual, full_pred)
    print(f"\nFull model test MAPE: {full_mape:.2f}%")

    results = []
    for group_name, features in feature_groups.items():
        remaining = [f for f in all_features if f not in features]
        X_abl = df[remaining].fillna(0).values
        X_tr, X_te = X_abl[:split], X_abl[split:]

        model = XGBRegressor(n_estimators=200, max_depth=4, random_state=42, n_jobs=-1, verbosity=0)
        model.fit(X_tr, y_train)
        pred = np.expm1(model.predict(X_te))
        abl_mape = mape(y_test_actual, pred)
        delta = abl_mape - full_mape
        results.append({"Group Removed": group_name, "MAPE": f"{abl_mape:.2f}%",
                        "Δ vs Full": f"{delta:+.2f}%"})
        print(f"  Without {group_name}: MAPE = {abl_mape:.2f}% (Δ = {delta:+.2f}%)")

    return pd.DataFrame(results)


def run_mortality_ablation():
    print("\n" + "=" * 60)
    print("ABLATION STUDY: Mortality Predictor")
    print("=" * 60)

    data_path = "ml_pipeline/data/processed/mortality_data_processed.csv"
    if not os.path.exists(data_path):
        print(f"  Data not found at {data_path}")
        return

    df = pd.read_csv(data_path)
    feature_groups = {
        "demographics": ["age_group_encoded", "district_encoded"],
        "temporal": ["month_sin", "month_cos", "season_flag", "year"],
        "lag_features": ["lag_1_month", "lag_3_month", "lag_6_month", "rolling_mean_3", "rolling_mean_6"],
    }
    all_features = ["age_group_encoded", "district_encoded", "month_sin", "month_cos",
                    "season_flag", "year", "lag_1_month", "lag_3_month", "lag_6_month",
                    "rolling_mean_3", "rolling_mean_6", "population_scaled"]
    available = [c for c in all_features if c in df.columns]

    X = df[available].fillna(0).values[:50000]
    y = df["death_rate"].fillna(0).values[:50000]
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]

    full_model = XGBRegressor(n_estimators=200, max_depth=4, random_state=42, n_jobs=-1, verbosity=0)
    full_model.fit(X_train, y_train)
    full_pred = full_model.predict(X_test)
    full_r2 = float(np.corrcoef(y_test, full_pred)[0, 1] ** 2) if len(np.unique(y_test)) > 1 else 0
    print(f"\nFull model test R²: {full_r2:.4f}")

    results = []
    for group_name, features in feature_groups.items():
        remaining = [f for f in available if f not in features]
        X_abl = df[remaining].fillna(0).values[:50000]
        X_tr, X_te = X_abl[:split], X_abl[split:]

        model = XGBRegressor(n_estimators=200, max_depth=4, random_state=42, n_jobs=-1, verbosity=0)
        model.fit(X_tr, y_train)
        pred = model.predict(X_te)
        abl_r2 = float(np.corrcoef(y_test, pred)[0, 1] ** 2) if len(np.unique(y_test)) > 1 else 0
        delta = abl_r2 - full_r2
        results.append({"Group Removed": group_name, "R²": f"{abl_r2:.4f}",
                        "Δ vs Full": f"{delta:+.4f}"})
        print(f"  Without {group_name}: R² = {abl_r2:.4f} (Δ = {delta:+.4f})")

    return pd.DataFrame(results)


if __name__ == "__main__":
    print("=" * 60)
    print("ABLATION STUDIES — All Models")
    print("=" * 60)

    results = {}
    results["forecast"] = run_forecast_ablation()
    results["scenario"] = run_scenario_ablation()
    results["mortality"] = run_mortality_ablation()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for model_name, df_result in results.items():
        if df_result is not None and not df_result.empty:
            print(f"\n{model_name.upper()}:")
            print(df_result.to_string(index=False))

    db.close()
    print("\nAblation studies complete!")
