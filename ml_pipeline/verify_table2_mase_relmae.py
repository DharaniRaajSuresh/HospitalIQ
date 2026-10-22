"""
verify_table2_mase_relmae.py
Computes:
1. Standard Hyndman-Koehler MASE (single global ratio: test_MAE / in_sample_naive_MAE)
2. Out-of-Sample Relative MAE (RelMAE: test_model_MAE / test_persistence_MAE)
3. Sample-weighted aggregation checks for Table II.
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
    test["persist_cases"] = test["lag_1_cases"]
    test["persist_deaths"] = test["lag_1_deaths"]

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

    # Valid non-zero death subsets
    test_nonzero_deaths = test[test["target_deaths"] > 0].copy()
    real_nonzero_deaths = real_stratum[real_stratum["target_deaths"] > 0].copy()
    synth_nonzero_deaths = synth_stratum[synth_stratum["target_deaths"] > 0].copy()

    # Standard Hyndman-Koehler MASE: single ratio = test_MAE / in_sample_naive_MAE
    # Cases:
    cases_all_mae = float(np.mean(np.abs(test["target_cases"] - test["pred_cases"])))
    cases_real_mae = float(np.mean(np.abs(real_stratum["target_cases"] - real_stratum["pred_cases"])))
    cases_synth_mae = float(np.mean(np.abs(synth_stratum["target_cases"] - synth_stratum["pred_cases"])))

    cases_all_persist_mae = float(np.mean(np.abs(test["target_cases"] - test["persist_cases"])))
    cases_real_persist_mae = float(np.mean(np.abs(real_stratum["target_cases"] - real_stratum["persist_cases"])))
    cases_synth_persist_mae = float(np.mean(np.abs(synth_stratum["target_cases"] - synth_stratum["persist_cases"])))

    covid_insample_cases_mae = per_disease_cases_mae["COVID-19"]
    covid_insample_deaths_mae = per_disease_deaths_mae["COVID-19"]

    mase_cases_real_hk = cases_real_mae / covid_insample_cases_mae
    relmae_cases_real = cases_real_mae / cases_real_persist_mae

    # Deaths (non-zero evaluation windows per Table II note):
    deaths_all_mae = float(np.mean(np.abs(test_nonzero_deaths["target_deaths"] - test_nonzero_deaths["pred_deaths"])))
    deaths_real_mae = float(np.mean(np.abs(real_nonzero_deaths["target_deaths"] - real_nonzero_deaths["pred_deaths"])))
    deaths_synth_mae = float(np.mean(np.abs(synth_nonzero_deaths["target_deaths"] - synth_nonzero_deaths["pred_deaths"])))

    deaths_all_persist_mae = float(np.mean(np.abs(test_nonzero_deaths["target_deaths"] - test_nonzero_deaths["persist_deaths"])))
    deaths_real_persist_mae = float(np.mean(np.abs(real_nonzero_deaths["target_deaths"] - real_nonzero_deaths["persist_deaths"])))
    deaths_synth_persist_mae = float(np.mean(np.abs(synth_nonzero_deaths["target_deaths"] - synth_nonzero_deaths["persist_deaths"])))

    mase_deaths_real_hk = deaths_real_mae / covid_insample_deaths_mae
    relmae_deaths_real = deaths_real_mae / deaths_real_persist_mae

    # Weighted per-disease in-sample MAE for synth and all strata:
    # Synth cases in-sample MAE (weighted by test disease distribution):
    synth_cases_weights = synth_stratum["disease"].value_counts(normalize=True).to_dict()
    synth_insample_cases_mae = sum(weight * per_disease_cases_mae[dis] for dis, weight in synth_cases_weights.items())
    mase_cases_synth_hk = cases_synth_mae / synth_insample_cases_mae
    relmae_cases_synth = cases_synth_mae / cases_synth_persist_mae

    all_cases_weights = test["disease"].value_counts(normalize=True).to_dict()
    all_insample_cases_mae = sum(weight * per_disease_cases_mae[dis] for dis, weight in all_cases_weights.items())
    mase_cases_all_hk = cases_all_mae / all_insample_cases_mae
    relmae_cases_all = cases_all_mae / cases_all_persist_mae

    # Synth deaths in-sample MAE:
    synth_deaths_weights = synth_nonzero_deaths["disease"].value_counts(normalize=True).to_dict()
    synth_insample_deaths_mae = sum(weight * per_disease_deaths_mae[dis] for dis, weight in synth_deaths_weights.items())
    mase_deaths_synth_hk = deaths_synth_mae / synth_insample_deaths_mae
    relmae_deaths_synth = deaths_synth_mae / deaths_synth_persist_mae

    all_deaths_weights = test_nonzero_deaths["disease"].value_counts(normalize=True).to_dict()
    all_insample_deaths_mae = sum(weight * per_disease_deaths_mae[dis] for dis, weight in all_deaths_weights.items())
    mase_deaths_all_hk = deaths_all_mae / all_insample_deaths_mae
    relmae_deaths_all = deaths_all_mae / deaths_all_persist_mae

    # Weighted MASE arithmetic check for Table II:
    # (170 * mase_deaths_real + 2775 * mase_deaths_synth) / 2945
    weighted_mase_deaths_all = (len(real_nonzero_deaths) * mase_deaths_real_hk + len(synth_nonzero_deaths) * mase_deaths_synth_hk) / len(test_nonzero_deaths)
    weighted_relmae_deaths_all = (len(real_nonzero_deaths) * relmae_deaths_real + len(synth_nonzero_deaths) * relmae_deaths_synth) / len(test_nonzero_deaths)

    results = {
        "sample_counts": {
            "n_test_all_cases": len(test),
            "n_real_cases": len(real_stratum),
            "n_synth_cases": len(synth_stratum),
            "n_test_all_deaths_nonzero": len(test_nonzero_deaths),
            "n_real_deaths_nonzero": len(real_nonzero_deaths),
            "n_synth_deaths_nonzero": len(synth_nonzero_deaths)
        },
        "cases_table_metrics": {
            "all": {"mae": round(cases_all_mae, 2), "hk_mase": round(mase_cases_all_hk, 4), "rel_mae": round(relmae_cases_all, 4)},
            "real": {"mae": round(cases_real_mae, 2), "hk_mase": round(mase_cases_real_hk, 4), "rel_mae": round(relmae_cases_real, 4)},
            "synth": {"mae": round(cases_synth_mae, 2), "hk_mase": round(mase_cases_synth_hk, 4), "rel_mae": round(relmae_cases_synth, 4)}
        },
        "deaths_table_metrics": {
            "all": {"mae": round(deaths_all_mae, 2), "hk_mase": round(mase_deaths_all_hk, 4), "rel_mae": round(relmae_deaths_all, 4), "weighted_mase_check": round(weighted_mase_deaths_all, 4)},
            "real": {"mae": round(deaths_real_mae, 2), "hk_mase": round(mase_deaths_real_hk, 4), "rel_mae": round(relmae_deaths_real, 4)},
            "synth": {"mae": round(deaths_synth_mae, 2), "hk_mase": round(mase_deaths_synth_hk, 4), "rel_mae": round(relmae_deaths_synth, 4)}
        }
    }

    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
