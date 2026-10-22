"""
test_real_surveillance_experiment.py
Authentic Empirical Surveillance Contamination Sweep:
1. Extracts genuine COVID-19 surveillance records (March 2020 - July 2021, N=510, 30 states x 17 months).
2. Sets up temporal train/test split:
   - Train: June 2020 - March 2021 (Wave 1 + inter-wave lull)
   - Test: April 2021 - July 2021 (Delta Wave - 100% AUTHENTIC REAL DATA)
3. Evaluates both Raw Cases and Differenced Target (to test tree extrapolation barrier).
4. Runs Controlled Contamination Sweep:
   - Blends synthetic tail data into training at rho in [0.0, 0.05, 0.10, 0.20, 0.35, 0.50, 0.85]
   - Evaluates strictly on the 100% REAL HELD-OUT TEST SET.
"""

import numpy as np
import pandas as pd
import math
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score

def compute_wape(y_true, y_pred):
    denom = np.sum(y_true)
    if denom == 0:
        return 0.0
    return np.sum(np.abs(y_true - y_pred)) / denom * 100.0

def run_experiment():
    print("=" * 80)
    print("STEP 1: LOADING & AUDITING RAW DATASET")
    print("=" * 80)
    df = pd.read_csv("ml_pipeline/data/raw/outbreak_real.csv")
    cov = df[df["disease"] == "COVID-19"].copy()
    cov["date"] = pd.to_datetime(cov["date"])
    cov = cov.sort_values(["state", "date"]).reset_index(drop=True)

    real_cov = cov[cov["date"] <= "2021-07-31"].copy()
    synth_cov = cov[cov["date"] > "2021-07-31"].copy()
    print(f"Total COVID rows: {len(cov)}")
    print(f"Authentic surveillance rows (<= 2021-07-31): {len(real_cov)}")
    print(f"Synthetic tail continuation rows (> 2021-07-31): {len(synth_cov)}")
    print(f"States: {real_cov['state'].nunique()}, Unique Dates: {real_cov['date'].nunique()}")

    # Build sequential lag dataset for all states
    def build_lag_features(data_source):
        records = []
        for state, group in data_source.groupby("state"):
            g = group.sort_values("date").reset_index(drop=True)
            if len(g) < 4:
                continue
            for i in range(3, len(g)):
                row = g.iloc[i]
                lag1 = g.iloc[i-1]
                lag2 = g.iloc[i-2]
                lag3 = g.iloc[i-3]
                
                m = row["date"].month
                records.append({
                    "date": row["date"],
                    "state": state,
                    "month": m,
                    "month_sin": math.sin(2 * math.pi * m / 12),
                    "month_cos": math.cos(2 * math.pi * m / 12),
                    "lag_1_cases": lag1["confirmed_cases"],
                    "lag_2_cases": lag2["confirmed_cases"],
                    "lag_3_cases": lag3["confirmed_cases"],
                    "cases_ma3": (lag1["confirmed_cases"] + lag2["confirmed_cases"] + lag3["confirmed_cases"]) / 3.0,
                    "lag_1_diff": lag1["confirmed_cases"] - lag2["confirmed_cases"],
                    "target_cases": row["confirmed_cases"],
                    "target_diff": row["confirmed_cases"] - lag1["confirmed_cases"],
                    "is_real": row["is_real"] if "is_real" in row else True
                })
        return pd.DataFrame(records)

    real_features = build_lag_features(real_cov)
    synth_features = build_lag_features(synth_cov)
    print(f"Real feature windows generated: {len(real_features)}")
    print(f"Synthetic feature windows available: {len(synth_features)}")

    # Split Real into Train (pre-April 2021) and Test (April 2021 - July 2021 Delta wave)
    train_real = real_features[real_features["date"] < "2021-04-01"].copy()
    test_real = real_features[real_features["date"] >= "2021-04-01"].copy()

    print(f"\nReal Train Windows (June 2020 - March 2021): {len(train_real)}")
    print(f"Real Test Windows (April 2021 - July 2021 Delta Wave): {len(test_real)}")

    feature_cols = ["month_sin", "month_cos", "lag_1_cases", "lag_2_cases", "lag_3_cases", "cases_ma3"]

    print("\n" + "=" * 80)
    print("STEP 2: TESTING TREE EXTRAPOLATION BARRIER ON DELTA WAVE")
    print("=" * 80)

    # 1. Raw Cases Model
    xgb_raw = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_raw.fit(train_real[feature_cols], train_real["target_cases"])
    pred_raw = xgb_raw.predict(test_real[feature_cols])
    pred_raw = np.maximum(0, pred_raw)

    mape_raw = mean_absolute_percentage_error(test_real["target_cases"], pred_raw) * 100
    wape_raw = compute_wape(test_real["target_cases"].values, pred_raw)
    r2_raw = r2_score(test_real["target_cases"], pred_raw)

    print(f"Raw Cases XGBoost on Delta Test Set:")
    print(f"  - Test MAPE: {mape_raw:.2f}%")
    print(f"  - Test WAPE: {wape_raw:.2f}%")
    print(f"  - Test R^2:  {r2_raw:.4f}")

    # Persistence Baseline on Test Set
    pred_persist = test_real["lag_1_cases"].values
    mape_persist = mean_absolute_percentage_error(test_real["target_cases"], pred_persist) * 100
    wape_persist = compute_wape(test_real["target_cases"].values, pred_persist)
    r2_persist = r2_score(test_real["target_cases"], pred_persist)
    print(f"\nNaive Lag-1 Persistence on Delta Test Set:")
    print(f"  - Test MAPE: {mape_persist:.2f}%")
    print(f"  - Test WAPE: {wape_persist:.2f}%")
    print(f"  - Test R^2:  {r2_persist:.4f}")

    # 2. Differenced Target Model (predicting delta y_t = y_t - y_{t-1})
    diff_feature_cols = ["month_sin", "month_cos", "lag_1_diff", "lag_1_cases", "cases_ma3"]
    xgb_diff = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_diff.fit(train_real[diff_feature_cols], train_real["target_diff"])
    pred_delta = xgb_diff.predict(test_real[diff_feature_cols])
    pred_diff_cases = test_real["lag_1_cases"].values + pred_delta
    pred_diff_cases = np.maximum(0, pred_diff_cases)

    mape_diff = mean_absolute_percentage_error(test_real["target_cases"], pred_diff_cases) * 100
    wape_diff = compute_wape(test_real["target_cases"].values, pred_diff_cases)
    r2_diff = r2_score(test_real["target_cases"], pred_diff_cases)

    print(f"\nDifferenced Target XGBoost on Delta Test Set:")
    print(f"  - Test MAPE: {mape_diff:.2f}%")
    print(f"  - Test WAPE: {wape_diff:.2f}%")
    print(f"  - Test R^2:  {r2_diff:.4f}")

    print("\n" + "=" * 80)
    print("STEP 3: CONTROLLED SYNTHETIC CONTAMINATION SWEEP (TESTED ON 100% REAL DELTA SET)")
    print("=" * 80)
    print(f"{'Contam. Ratio (rho)':<22} | {'Train N':<10} | {'Test WAPE':<12} | {'Test MAPE':<12} | {'Test R^2':<12} | {'Relative Delta WAPE'}")
    print("-" * 88)

    rhos = [0.00, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 0.85]
    sweep_results = []
    base_wape = None

    for rho in rhos:
        if rho == 0.0:
            train_curr = train_real.copy()
        else:
            n_real = len(train_real)
            # rho = n_synth / (n_real + n_synth) => n_synth = n_real * rho / (1 - rho)
            n_synth = int(n_real * rho / (1.0 - rho))
            sample_synth = synth_features.sample(n=min(n_synth, len(synth_features)), random_state=42)
            train_curr = pd.concat([train_real, sample_synth], ignore_index=True)

        model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
        model.fit(train_curr[feature_cols], train_curr["target_cases"])
        pred = model.predict(test_real[feature_cols])
        pred = np.maximum(0, pred)

        wape = compute_wape(test_real["target_cases"].values, pred)
        mape = mean_absolute_percentage_error(test_real["target_cases"], pred) * 100
        r2 = r2_score(test_real["target_cases"], pred)

        if base_wape is None:
            base_wape = wape
            rel_delta = "0.00% (Baseline)"
        else:
            rel_delta = f"{(wape - base_wape):>+6.2f}%"

        sweep_results.append((rho, len(train_curr), wape, mape, r2))
        print(f"{rho*100:>5.1f}%{'':<16} | {len(train_curr):<10} | {wape:>6.2f}%{'':<5} | {mape:>6.2f}%{'':<5} | {r2:>7.4f}{'':<4} | {rel_delta}")

    print("-" * 88)
    print("Sweep complete. Data ready for analysis.")

if __name__ == "__main__":
    run_experiment()
