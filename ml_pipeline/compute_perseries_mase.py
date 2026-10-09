"""
compute_perseries_mase.py
Computes textbook Hyndman-Koehler MASE using per-disease in-sample naive persistence MAE denominators.
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

    # Compute PER-DISEASE in-sample naive 1-step MAE
    per_disease_cases_mae = {}
    per_disease_deaths_mae = {}

    for disease, group in train.groupby("disease"):
        diffs_cases = []
        diffs_deaths = []
        for state, s_group in group.groupby("state"):
            c = s_group.sort_values(["year", "month"])["target_cases"].to_numpy()
            d = s_group.sort_values(["year", "month"])["target_deaths"].to_numpy()
            if len(c) > 1:
                diffs_cases.extend(np.abs(np.diff(c)))
            if len(d) > 1:
                diffs_deaths.extend(np.abs(np.diff(d)))
        per_disease_cases_mae[disease] = float(np.mean(diffs_cases)) if diffs_cases else 1.0
        per_disease_deaths_mae[disease] = float(np.mean(diffs_deaths)) if diffs_deaths else 1.0

    # Join with raw CSV to flag real COVID stratum
    raw_df = pd.read_csv("ml_pipeline/data/raw/outbreak_real.csv")
    raw_df["dt"] = pd.to_datetime(raw_df["date"])
    raw_df["year"] = raw_df["dt"].dt.year
    raw_df["month"] = raw_df["dt"].dt.month
    cov_real_keys = set(raw_df[(raw_df["disease"] == "COVID-19") & (raw_df["is_real"] == 1)][["disease", "state", "year", "month"]].itertuples(index=False, name=None))

    test["is_real_stratum"] = test.apply(lambda r: (r["disease"], r["state"], r["year"], r["month"]) in cov_real_keys, axis=1)

    real_stratum = test[test["is_real_stratum"]].copy()
    synth_stratum = test[~test["is_real_stratum"]].copy()

    # Textbook MASE per row: |y_t - y_hat_t| / naive_mae_of_that_disease
    test["cases_mase_row"] = test.apply(lambda r: abs(r["target_cases"] - r["pred_cases"]) / per_disease_cases_mae[r["disease"]], axis=1)
    test["deaths_mase_row"] = test.apply(lambda r: abs(r["target_deaths"] - r["pred_deaths"]) / per_disease_deaths_mae[r["disease"]], axis=1)

    real_stratum["cases_mase_row"] = real_stratum.apply(lambda r: abs(r["target_cases"] - r["pred_cases"]) / per_disease_cases_mae[r["disease"]], axis=1)
    real_stratum["deaths_mase_row"] = real_stratum.apply(lambda r: abs(r["target_deaths"] - r["pred_deaths"]) / per_disease_deaths_mae[r["disease"]], axis=1)

    synth_stratum["cases_mase_row"] = synth_stratum.apply(lambda r: abs(r["target_cases"] - r["pred_cases"]) / per_disease_cases_mae[r["disease"]], axis=1)
    synth_stratum["deaths_mase_row"] = synth_stratum.apply(lambda r: abs(r["target_deaths"] - r["pred_deaths"]) / per_disease_deaths_mae[r["disease"]], axis=1)

    # COVID-only in-sample naive MAE specifically:
    covid_in_sample_cases_mae = per_disease_cases_mae.get("COVID-19", 1.0)
    covid_in_sample_deaths_mae = per_disease_deaths_mae.get("COVID-19", 1.0)

    results = {
        "per_disease_in_sample_naive_mae": {
            "cases": per_disease_cases_mae,
            "deaths": per_disease_deaths_mae
        },
        "covid_in_sample_naive_mae": {
            "cases_mae": covid_in_sample_cases_mae,
            "deaths_mae": covid_in_sample_deaths_mae
        },
        "textbook_mase_results": {
            "cases_all": {
                "mae": float(np.mean(np.abs(test["target_cases"] - test["pred_cases"]))),
                "mase_mean": float(np.mean(test["cases_mase_row"])),
                "mase_median": float(np.median(test["cases_mase_row"]))
            },
            "cases_real_covid_stratum": {
                "mae": float(np.mean(np.abs(real_stratum["target_cases"] - real_stratum["pred_cases"]))),
                "mase_mean": float(np.mean(real_stratum["cases_mase_row"])),
                "mase_median": float(np.median(real_stratum["cases_mase_row"])),
                "mase_direct_ratio": float(np.mean(np.abs(real_stratum["target_cases"] - real_stratum["pred_cases"])) / covid_in_sample_cases_mae)
            },
            "cases_synth_stratum": {
                "mae": float(np.mean(np.abs(synth_stratum["target_cases"] - synth_stratum["pred_cases"]))),
                "mase_mean": float(np.mean(synth_stratum["cases_mase_row"])),
                "mase_median": float(np.median(synth_stratum["cases_mase_row"]))
            },
            "deaths_all": {
                "mae": float(np.mean(np.abs(test["target_deaths"] - test["pred_deaths"]))),
                "mase_mean": float(np.mean(test["deaths_mase_row"])),
                "mase_median": float(np.median(test["deaths_mase_row"]))
            },
            "deaths_real_covid_stratum": {
                "mae": float(np.mean(np.abs(real_stratum["target_deaths"] - real_stratum["pred_deaths"]))),
                "mase_mean": float(np.mean(real_stratum["deaths_mase_row"])),
                "mase_median": float(np.median(real_stratum["deaths_mase_row"])),
                "mase_direct_ratio": float(np.mean(np.abs(real_stratum["target_deaths"] - real_stratum["pred_deaths"])) / covid_in_sample_deaths_mae)
            },
            "deaths_synth_stratum": {
                "mae": float(np.mean(np.abs(synth_stratum["target_deaths"] - synth_stratum["pred_deaths"]))),
                "mase_mean": float(np.mean(synth_stratum["deaths_mase_row"])),
                "mase_median": float(np.median(synth_stratum["deaths_mase_row"]))
            }
        }
    }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
