"""
compute_exact_mase.py
Computes standard Hyndman-Koehler MASE for Table II using in-sample 1-step naive persistence MAE denominator.
"""

import json
import sqlite3
import math
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

FEATURE_COLUMNS = [
    "month_sin", "month_cos", "year_normalized",
    "lag_1_cases", "lag_2_cases", "lag_3_cases",
    "lag_1_deaths", "lag_2_deaths", "cases_ma3", "cases_growth",
    "disease_cfr", "disease_r0", "state_beds", "state_hospitals",
    "disease_enc", "state_enc",
]

def load_data():
    db_path = Path("ml_pipeline/data/hospitaliq.db")
    with sqlite3.connect(f"file:{db_path.resolve()}?mode=ro", uri=True) as conn:
        frame = pd.read_sql_query("""
            SELECT disease, state, year, month,
                   SUM(confirmed_cases) AS cases,
                   SUM(deaths) AS deaths,
                   AVG(case_fatality_rate) AS avg_cfr,
                   AVG(reproduction_rate) AS avg_r0
            FROM pandemic_outbreak
            GROUP BY disease, state, year, month
            ORDER BY disease, state, year, month
        """, conn)
        capacity_rows = pd.read_sql_query("""
            SELECT state, COALESCE(SUM(total_beds), 0) AS total_beds, COUNT(DISTINCT hospital_name) AS hospitals
            FROM hospital_beds GROUP BY state
        """, conn)

    capacity = {str(row.state): {"total_beds": int(row.total_beds or 0), "hospitals": int(row.hospitals or 0)} for row in capacity_rows.itertuples(index=False)}
    
    disease_params = {}
    for disease, group in frame.groupby("disease", sort=False):
        disease_params[disease] = {"cfr": float(group["avg_cfr"].mean()), "r0": float(group["avg_r0"].mean())}

    records = []
    for (disease, state), group in frame.groupby(["disease", "state"], sort=True):
        sequence = group.sort_values(["year", "month"]).reset_index(drop=True)
        if len(sequence) < 4:
            continue
        for idx in range(3, len(sequence)):
            row = sequence.iloc[idx]
            lag1 = sequence.iloc[idx - 1]
            lag2 = sequence.iloc[idx - 2]
            lag3 = sequence.iloc[idx - 3]
            month = int(row["month"])
            previous_cases = [float(lag1.cases), float(lag2.cases), float(lag3.cases)]
            params = disease_params[disease]
            records.append({
                "disease": disease,
                "state": state,
                "year": int(row["year"]),
                "month": month,
                "month_sin": math.sin(2 * math.pi * month / 12),
                "month_cos": math.cos(2 * math.pi * month / 12),
                "year_normalized": (int(row["year"]) - 2017) / 15,
                "lag_1_cases": previous_cases[0],
                "lag_2_cases": previous_cases[1],
                "lag_3_cases": previous_cases[2],
                "lag_1_deaths": float(lag1["deaths"]),
                "lag_2_deaths": float(lag2["deaths"]),
                "cases_ma3": sum(previous_cases) / 3,
                "cases_growth": (previous_cases[0] - previous_cases[1]) / max(previous_cases[1], 1),
                "disease_cfr": params["cfr"],
                "disease_r0": params["r0"],
                "state_beds": capacity.get(state, {"total_beds": 1000})["total_beds"],
                "state_hospitals": capacity.get(state, {"hospitals": 10}).get("hospitals", 10),
                "target_cases": float(row["cases"] or 0),
                "target_deaths": float(row["deaths"] or 0),
            })
    
    windows = pd.DataFrame.from_records(records)
    disease_enc = {v: i for i, v in enumerate(sorted(windows.disease.unique()))}
    state_enc = {v: i for i, v in enumerate(sorted(windows.state.unique()))}
    windows["disease_enc"] = windows["disease"].map(disease_enc)
    windows["state_enc"] = windows["state"].map(state_enc)
    return windows

def main():
    windows = load_data()
    ordered = windows.sort_values(["year", "month"]).reset_index(drop=True)
    split = int(len(ordered) * 0.85)
    train = ordered.iloc[:split].copy()
    test = ordered.iloc[split:].copy()

    model_dir = Path("ml_pipeline/data/models")
    cases_model = joblib.load(model_dir / "forecast_cases_model.pkl")
    deaths_model = joblib.load(model_dir / "forecast_deaths_model.pkl")

    features = test[FEATURE_COLUMNS].fillna(0).to_numpy()
    cases_pred = np.maximum(0, np.expm1(cases_model.predict(features)))
    deaths_pred = np.maximum(0, np.expm1(deaths_model.predict(features)))

    test["pred_cases"] = cases_pred
    test["pred_deaths"] = deaths_pred

    # Calculate in-sample naive 1-step MAE per series
    train_diff_cases = []
    for (d, s), group in train.groupby(["disease", "state"]):
        c = group["target_cases"].to_numpy()
        if len(c) > 1:
            train_diff_cases.extend(np.abs(np.diff(c)))
    naive_mae_cases_insample = np.mean(train_diff_cases)

    train_diff_deaths = []
    for (d, s), group in train.groupby(["disease", "state"]):
        d_vals = group["target_deaths"].to_numpy()
        if len(d_vals) > 1:
            train_diff_deaths.extend(np.abs(np.diff(d_vals)))
    naive_mae_deaths_insample = np.mean(train_diff_deaths)

    # Join with outbreak_real.csv for provenance flag
    raw_df = pd.read_csv("ml_pipeline/data/raw/outbreak_real.csv")
    raw_df["dt"] = pd.to_datetime(raw_df["date"])
    raw_df["year"] = raw_df["dt"].dt.year
    raw_df["month"] = raw_df["dt"].dt.month
    cov_real_keys = set(raw_df[(raw_df["disease"] == "COVID-19") & (raw_df["is_real"] == 1)][["disease", "state", "year", "month"]].itertuples(index=False, name=None))

    test["is_real_stratum"] = test.apply(lambda r: (r["disease"], r["state"], r["year"], r["month"]) in cov_real_keys, axis=1)

    real_stratum = test[test["is_real_stratum"]]
    synth_stratum = test[~test["is_real_stratum"]]

    def calc_mase(y_true, y_pred, naive_mae):
        mae = np.mean(np.abs(y_true - y_pred))
        return mae / naive_mae if naive_mae > 0 else float("nan")

    results = {
        "naive_mae_cases_insample": float(naive_mae_cases_insample),
        "naive_mae_deaths_insample": float(naive_mae_deaths_insample),
        "cases_all": {
            "mae": float(np.mean(np.abs(test["target_cases"] - test["pred_cases"]))),
            "mase": float(calc_mase(test["target_cases"].to_numpy(), test["pred_cases"].to_numpy(), naive_mae_cases_insample))
        },
        "cases_real": {
            "mae": float(np.mean(np.abs(real_stratum["target_cases"] - real_stratum["pred_cases"]))),
            "mase": float(calc_mase(real_stratum["target_cases"].to_numpy(), real_stratum["pred_cases"].to_numpy(), naive_mae_cases_insample))
        },
        "cases_synth": {
            "mae": float(np.mean(np.abs(synth_stratum["target_cases"] - synth_stratum["pred_cases"]))),
            "mase": float(calc_mase(synth_stratum["target_cases"].to_numpy(), synth_stratum["pred_cases"].to_numpy(), naive_mae_cases_insample))
        },
        "deaths_all": {
            "mae": float(np.mean(np.abs(test["target_deaths"] - test["pred_deaths"]))),
            "mase": float(calc_mase(test["target_deaths"].to_numpy(), test["pred_deaths"].to_numpy(), naive_mae_deaths_insample))
        },
        "deaths_real": {
            "mae": float(np.mean(np.abs(real_stratum["target_deaths"] - real_stratum["pred_deaths"]))),
            "mase": float(calc_mase(real_stratum["target_deaths"].to_numpy(), real_stratum["pred_deaths"].to_numpy(), naive_mae_deaths_insample))
        },
        "deaths_synth": {
            "mae": float(np.mean(np.abs(synth_stratum["target_deaths"] - synth_stratum["pred_deaths"]))),
            "mase": float(calc_mase(synth_stratum["target_deaths"].to_numpy(), synth_stratum["pred_deaths"].to_numpy(), naive_mae_deaths_insample))
        }
    }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
