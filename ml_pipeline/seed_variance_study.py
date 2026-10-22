import logging
import math
import os
import sys
import warnings
import json
import numpy as np
import pandas as pd
from sklearn.metrics import r2_score, mean_absolute_percentage_error
from sklearn.model_selection import GridSearchCV, train_test_split
from xgboost import XGBRegressor
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sqlalchemy import func

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, SCRIPT_DIR)

from backend.database import SessionLocal
from backend.models import HospitalBed, PandemicOutbreak
from train_patient_risk import generate_synthetic_data, FEATURE_NAMES

def main():
    db = SessionLocal()
    results = {
        "Forecast": {"train_r2": [], "test_r2": [], "test_mape": []},
        "Mortality": {"train_r2": [], "test_r2": [], "test_mape": []},
        "Bed": {"train_r2": [], "test_r2": [], "test_mape": []},
        "Patient Risk": {"train_r2": [], "test_r2": [], "test_mape": []},
        "Scenario": {"train_r2": [], "test_r2": [], "test_mape": []},
    }

    # --- 1. FORECAST DATA PREP ---
    print("Preparing Forecast data...")
    rows = db.query(
        PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year, PandemicOutbreak.month,
        func.sum(PandemicOutbreak.confirmed_cases).label("confirmed_cases"),
        func.sum(PandemicOutbreak.deaths).label("deaths"),
        func.avg(PandemicOutbreak.case_fatality_rate).label("avg_cfr"),
        func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0")
    ).group_by(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year, PandemicOutbreak.month).order_by(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year, PandemicOutbreak.month).all()

    state_beds = {}
    cap_rows = db.query(HospitalBed.state, func.sum(HospitalBed.total_beds).label("total_beds"), func.count(func.distinct(HospitalBed.hospital_name)).label("hospitals")).group_by(HospitalBed.state).all()
    for r in cap_rows:
        state_beds[r.state] = {"total_beds": int(r.total_beds or 0), "hospitals": int(r.hospitals or 0)}

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
        disease_avg_params[k]["cfr"] = disease_avg_params[k]["cfr_sum"] / max(disease_avg_params[k]["cfr_n"], 1)
        disease_avg_params[k]["r0"] = disease_avg_params[k]["r0_sum"] / max(disease_avg_params[k]["r0_n"], 1)

    records = []
    current_key = None
    buffer = []
    def flush_buffer():
        nonlocal buffer
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
                "disease": row["disease"], "state": row["state"], "year": row["year"], "month": row["month"],
                "month_sin": month_sin, "month_cos": month_cos, "year_normalized": year_norm,
                "lag_1_cases": lag1["cases"], "lag_2_cases": lag2["cases"], "lag_3_cases": lag3["cases"],
                "lag_1_deaths": lag1["deaths"], "lag_2_deaths": lag2["deaths"],
                "cases_ma3": cases_ma3, "cases_growth": cases_growth,
                "disease_cfr": disease_avg_params.get(row["disease"], {}).get("cfr", 0),
                "disease_r0": disease_avg_params.get(row["disease"], {}).get("r0", 0),
                "state_beds": cap["total_beds"], "state_hospitals": cap["hospitals"],
                "target_cases": row["cases"], "target_deaths": row["deaths"],
            })
        buffer = []

    for r in rows:
        key = (r.disease, r.state)
        entry = {"disease": r.disease, "state": r.state, "year": r.year, "month": r.month, "cases": int(r.confirmed_cases or 0), "deaths": int(r.deaths or 0)}
        if key != current_key:
            flush_buffer()
            current_key = key
            buffer = [entry]
        else:
            buffer.append(entry)
    flush_buffer()

    df_f = pd.DataFrame(records)
    disease_enc = {d: i for i, d in enumerate(sorted(df_f["disease"].unique()))}
    state_enc = {s: i for i, s in enumerate(sorted(df_f["state"].unique()))}
    df_f["disease_enc"] = df_f["disease"].map(disease_enc)
    df_f["state_enc"] = df_f["state"].map(state_enc)
    feature_cols_f = ["month_sin", "month_cos", "year_normalized", "lag_1_cases", "lag_2_cases", "lag_3_cases", "lag_1_deaths", "lag_2_deaths", "cases_ma3", "cases_growth", "disease_cfr", "disease_r0", "state_beds", "state_hospitals", "disease_enc", "state_enc"]
    X_f = df_f[feature_cols_f].fillna(0).values
    y_f_cases = np.log1p(df_f["target_cases"].values)
    df_f_sorted = df_f.sort_values(["year", "month"])
    split_idx = int(len(df_f_sorted) * 0.85)
    train_idx = df_f_sorted.index[:split_idx]
    test_idx = df_f_sorted.index[split_idx:]
    X_f_train, X_f_test = X_f[train_idx], X_f[test_idx]
    y_f_train, y_f_test = y_f_cases[train_idx], y_f_cases[test_idx]
    PARAM_GRID_F = {"n_estimators": [100], "max_depth": [4], "learning_rate": [0.1], "subsample": [0.8], "colsample_bytree": [0.8], "reg_lambda": [1.0]}

    # --- 2. MORTALITY DATA PREP ---
    print("Preparing Mortality data...")
    CSV_PATH_M = os.path.join(SCRIPT_DIR, "data", "processed", "mortality_data_processed.csv")
    df_m = pd.read_csv(CSV_PATH_M).dropna(subset=["state_encoded", "district_encoded", "age_group_encoded", "cause_encoded", "year", "population_scaled", "month_sin", "month_cos", "season_flag", "lag_1_month", "lag_3_month", "lag_6_month", "rolling_mean_3", "rolling_mean_6", "death_rate"])
    df_m = df_m.sort_values(["state_encoded", "district_encoded", "year", "month"])
    X_m = df_m[["state_encoded", "district_encoded", "age_group_encoded", "cause_encoded", "year", "population_scaled", "month_sin", "month_cos", "season_flag", "lag_1_month", "lag_3_month", "lag_6_month", "rolling_mean_3", "rolling_mean_6"]].values
    y_m = df_m["death_rate"].values
    split_m = int(len(df_m) * 0.85)
    X_m_train, X_m_test = X_m[:split_m], X_m[split_m:]
    y_m_train, y_m_test = y_m[:split_m], y_m[split_m:]

    # --- 3. BED DATA PREP ---
    print("Preparing Bed data...")
    CSV_PATH_B = os.path.join(SCRIPT_DIR, "data", "processed", "bed_data_processed.csv")
    df_b = pd.read_csv(CSV_PATH_B).sort_values(["state_encoded", "ward_type_encoded", "recorded_year", "recorded_month"]).dropna(subset=["month_sin", "month_cos", "year_normalized", "season_flag", "state_encoded", "ward_type_encoded", "lag_1_month", "lag_3_month", "lag_6_month", "rolling_mean_3", "rolling_mean_6", "available_beds"])
    X_b = df_b[["month_sin", "month_cos", "year_normalized", "season_flag", "state_encoded", "ward_type_encoded", "lag_1_month", "lag_3_month", "lag_6_month", "rolling_mean_3", "rolling_mean_6"]].values
    y_b = df_b["available_beds"].values
    X_b_train, X_b_test, y_b_train, y_b_test = train_test_split(X_b, y_b, test_size=0.2, random_state=42)

    # --- 4. PATIENT RISK DATA PREP ---
    print("Preparing Patient Risk data...")
    df_p = generate_synthetic_data(n_patients=5000)
    X_p = df_p[FEATURE_NAMES].values
    y_p = df_p["risk_score"].values
    X_p_train, X_p_test, y_p_train, y_p_test = train_test_split(X_p, y_p, test_size=0.2, random_state=42)

    # --- 5. SCENARIO DATA PREP ---
    print("Preparing Scenario data...")
    rows_s = db.query(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year, func.sum(PandemicOutbreak.confirmed_cases).label("total_cases"), func.avg(PandemicOutbreak.case_fatality_rate).label("avg_cfr"), func.avg(PandemicOutbreak.reproduction_rate).label("avg_r0")).group_by(PandemicOutbreak.disease, PandemicOutbreak.state, PandemicOutbreak.year).all()
    disease_enc_s = {}
    state_enc_s = {}
    records_s = []
    for r in rows_s:
        if r.disease not in disease_enc_s: disease_enc_s[r.disease] = len(disease_enc_s)
        if r.state not in state_enc_s: state_enc_s[r.state] = len(state_enc_s)
        cap = state_beds.get(r.state, {"total_beds": 1000, "hospitals": 10})
        records_s.append({
            "target_year_norm": (r.year - 2017)/15,
            "avg_cfr": float(r.avg_cfr or 1.0),
            "avg_r0": float(r.avg_r0 or 2.0),
            "state_beds": cap["total_beds"],
            "state_hospitals": cap["hospitals"],
            "disease_enc": disease_enc_s[r.disease],
            "state_enc": state_enc_s[r.state],
            "total_cases": int(r.total_cases or 0)
        })
    df_s = pd.DataFrame(records_s)
    X_s = df_s[["target_year_norm", "avg_cfr", "avg_r0", "state_beds", "state_hospitals", "disease_enc", "state_enc"]].fillna(0).values
    y_s = np.log1p(df_s["total_cases"].values)
    df_s_sorted = df_s.sort_values("target_year_norm")
    split_idx_s = int(len(df_s_sorted) * 0.85)
    train_idx_s = df_s_sorted.index[:split_idx_s]
    test_idx_s = df_s_sorted.index[split_idx_s:]
    X_s_train, X_s_test = X_s[train_idx_s], X_s[test_idx_s]
    y_s_train, y_s_test = y_s[train_idx_s], y_s[test_idx_s]

    db.close()

    def mape_fn(y_true, y_pred):
        mask = y_true > 0
        return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100

    def get_mape(y_true, y_pred, is_log=False):
        if is_log:
            return mape_fn(np.expm1(y_true), np.expm1(y_pred))
        return mape_fn(y_true, y_pred)

    print("\nStarting iterations...")
    for seed in range(10):
        print(f"\n--- Seed {seed} ---")
        
        # 1. Forecast
        base_f = XGBRegressor(random_state=seed, n_jobs=-1, verbosity=0)
        grid_f = GridSearchCV(base_f, PARAM_GRID_F, cv=2, scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
        grid_f.fit(X_f_train, y_f_train)
        model_f = grid_f.best_estimator_
        train_r2_f = model_f.score(X_f_train, y_f_train)
        test_r2_f = model_f.score(X_f_test, y_f_test)
        test_mape_f = get_mape(y_f_test, model_f.predict(X_f_test), is_log=True)
        results["Forecast"]["train_r2"].append(float(train_r2_f))
        results["Forecast"]["test_r2"].append(float(test_r2_f))
        results["Forecast"]["test_mape"].append(float(test_mape_f))
        print(f"Forecast: test_R2={test_r2_f:.4f}, test_MAPE={test_mape_f:.2f}%")
        
        # 2. Mortality
        model_m = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0, random_state=seed, n_jobs=-1, verbosity=0)
        model_m.fit(X_m_train, y_m_train)
        train_r2_m = model_m.score(X_m_train, y_m_train)
        test_r2_m = model_m.score(X_m_test, y_m_test)
        test_mape_m = get_mape(y_m_test, model_m.predict(X_m_test))
        results["Mortality"]["train_r2"].append(float(train_r2_m))
        results["Mortality"]["test_r2"].append(float(test_r2_m))
        results["Mortality"]["test_mape"].append(float(test_mape_m))
        print(f"Mortality: test_R2={test_r2_m:.4f}, test_MAPE={test_mape_m:.2f}%")
        
        # 3. Bed
        model_b = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=seed)
        model_b.fit(X_b_train, y_b_train)
        train_r2_b = model_b.score(X_b_train, y_b_train)
        test_r2_b = model_b.score(X_b_test, y_b_test)
        test_mape_b = get_mape(y_b_test, model_b.predict(X_b_test))
        results["Bed"]["train_r2"].append(float(train_r2_b))
        results["Bed"]["test_r2"].append(float(test_r2_b))
        results["Bed"]["test_mape"].append(float(test_mape_b))
        print(f"Bed: test_R2={test_r2_b:.4f}, test_MAPE={test_mape_b:.2f}%")
        
        # 4. Patient Risk
        xgb_p = XGBRegressor(n_estimators=300, max_depth=8, learning_rate=0.1, subsample=0.8, colsample_bytree=0.8, random_state=seed, n_jobs=-1)
        rf_p = RandomForestRegressor(n_estimators=200, max_depth=15, min_samples_leaf=3, random_state=seed, n_jobs=-1)
        gb_p = GradientBoostingRegressor(n_estimators=200, max_depth=6, learning_rate=0.1, min_samples_leaf=3, random_state=seed)
        xgb_p.fit(X_p_train, y_p_train)
        rf_p.fit(X_p_train, y_p_train)
        gb_p.fit(X_p_train, y_p_train)
        pred_train_p = (xgb_p.predict(X_p_train) + rf_p.predict(X_p_train) + gb_p.predict(X_p_train)) / 3
        pred_test_p = (xgb_p.predict(X_p_test) + rf_p.predict(X_p_test) + gb_p.predict(X_p_test)) / 3
        train_r2_p = r2_score(y_p_train, pred_train_p)
        test_r2_p = r2_score(y_p_test, pred_test_p)
        test_mape_p = get_mape(y_p_test, pred_test_p)
        results["Patient Risk"]["train_r2"].append(float(train_r2_p))
        results["Patient Risk"]["test_r2"].append(float(test_r2_p))
        results["Patient Risk"]["test_mape"].append(float(test_mape_p))
        print(f"Patient Risk: test_R2={test_r2_p:.4f}, test_MAPE={test_mape_p:.2f}%")
        
        # 5. Scenario
        base_s = XGBRegressor(random_state=seed, n_jobs=-1, verbosity=0)
        grid_s = GridSearchCV(base_s, PARAM_GRID_F, cv=2, scoring="neg_mean_squared_error", n_jobs=-1, verbose=0)
        grid_s.fit(X_s_train, y_s_train)
        model_s = grid_s.best_estimator_
        train_r2_s = model_s.score(X_s_train, y_s_train)
        test_r2_s = model_s.score(X_s_test, y_s_test)
        test_mape_s = get_mape(y_s_test, model_s.predict(X_s_test), is_log=True)
        results["Scenario"]["train_r2"].append(float(train_r2_s))
        results["Scenario"]["test_r2"].append(float(test_r2_s))
        results["Scenario"]["test_mape"].append(float(test_mape_s))
        print(f"Scenario: test_R2={test_r2_s:.4f}, test_MAPE={test_mape_s:.2f}%")

    print("\n=== SUMMARY ===")
    output = {}
    for m, mets in results.items():
        tr_r2 = np.array(mets["train_r2"])
        te_r2 = np.array(mets["test_r2"])
        te_mape = np.array(mets["test_mape"])
        print(f"{m}:")
        print(f"  Train R²:  {tr_r2.mean():.4f} ± {tr_r2.std():.4f}")
        print(f"  Test R²:   {te_r2.mean():.4f} ± {te_r2.std():.4f}")
        print(f"  Test MAPE: {te_mape.mean():.2f}% ± {te_mape.std():.2f}%")
        output[m] = {
            "train_r2_mean": float(tr_r2.mean()), "train_r2_sd": float(tr_r2.std()),
            "test_r2_mean": float(te_r2.mean()), "test_r2_sd": float(te_r2.std()),
            "test_mape_mean": float(te_mape.mean()), "test_mape_sd": float(te_mape.std()),
        }

    output_path = os.path.join(SCRIPT_DIR, "seed_variance_results.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved results to {output_path}")

if __name__ == "__main__":
    main()
