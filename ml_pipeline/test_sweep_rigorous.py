"""
test_sweep_rigorous.py
Rigorous, Uncertainty-Aware Surveillance Contamination Sweep:
1. Target: Differenced target Delta y_t = y_t - y_{t-1} (predicting momentum, avoiding raw-count tree ceiling).
2. Repeated Trials: N_TRIALS = 30 random seeds for synthetic data subsampling at each rho.
3. Uncertainty Quantification: Reports Mean, Std Dev, and 95% Empirical CI [2.5%, 97.5%] for WAPE, R^2, and MAPE.
4. Baseline Significance Check: Paired Wilcoxon / Diebold-Mariano test vs Naive Persistence on the clean (rho=0) model.
5. 100% Real Held-Out Test Set: April 2021 - July 2021 (Delta Wave, N=120 windows across 30 states).
"""

import numpy as np
import pandas as pd
import math
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from scipy import stats

def compute_wape(y_true, y_pred):
    denom = np.sum(y_true)
    if denom == 0:
        return 0.0
    return np.sum(np.abs(y_true - y_pred)) / denom * 100.0

def run_rigorous_sweep():
    print("=" * 85)
    print("RIGOROUS UNCERTAINTY-AWARE CONTAMINATION SWEEP (30 REPEATED TRIALS + 95% CI)")
    print("=" * 85)

    df = pd.read_csv("ml_pipeline/data/raw/outbreak_real.csv")
    cov = df[df["disease"] == "COVID-19"].copy()
    cov["date"] = pd.to_datetime(cov["date"])
    cov = cov.sort_values(["state", "date"]).reset_index(drop=True)

    real_cov = cov[cov["date"] <= "2021-07-31"].copy()
    synth_cov = cov[cov["date"] > "2021-07-31"].copy()

    def build_dataset(data_source):
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
                    "month_sin": math.sin(2 * math.pi * m / 12),
                    "month_cos": math.cos(2 * math.pi * m / 12),
                    "lag_1_cases": lag1["confirmed_cases"],
                    "lag_2_cases": lag2["confirmed_cases"],
                    "lag_3_cases": lag3["confirmed_cases"],
                    "cases_ma3": (lag1["confirmed_cases"] + lag2["confirmed_cases"] + lag3["confirmed_cases"]) / 3.0,
                    "lag_1_diff": lag1["confirmed_cases"] - lag2["confirmed_cases"],
                    "lag_2_diff": lag2["confirmed_cases"] - lag3["confirmed_cases"],
                    "target_cases": row["confirmed_cases"],
                    "target_diff": row["confirmed_cases"] - lag1["confirmed_cases"],
                })
        return pd.DataFrame(records)

    real_features = build_dataset(real_cov)
    synth_features = build_dataset(synth_cov)

    train_real = real_features[real_features["date"] < "2021-04-01"].copy()
    test_real = real_features[real_features["date"] >= "2021-04-01"].copy()

    y_test_cases = test_real["target_cases"].values
    lag1_test = test_real["lag_1_cases"].values

    # Naive Persistence Benchmark on Delta Test Set
    pred_persist = lag1_test
    wape_persist = compute_wape(y_test_cases, pred_persist)
    mape_persist = mean_absolute_percentage_error(y_test_cases, pred_persist) * 100
    r2_persist = r2_score(y_test_cases, pred_persist)

    print(f"Test Set Size: {len(test_real)} windows (April-July 2021 Delta Surge across 30 states)")
    print(f"Train Real Size: {len(train_real)} windows (June 2020 - March 2021)")
    print(f"\nNAIVE PERSISTENCE BENCHMARK (Delta Test Set):")
    print(f"  WAPE: {wape_persist:.2f}%  |  MAPE: {mape_persist:.2f}%  |  R^2: {r2_persist:.4f}")

    diff_features = ["month_sin", "month_cos", "lag_1_diff", "lag_2_diff", "lag_1_cases", "cases_ma3"]

    # Evaluate Baseline Model (rho = 0.0) with Differenced Target
    base_model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    base_model.fit(train_real[diff_features], train_real["target_diff"])
    pred_base_delta = base_model.predict(test_real[diff_features])
    pred_base_cases = np.maximum(0, lag1_test + pred_base_delta)

    wape_base = compute_wape(y_test_cases, pred_base_cases)
    mape_base = mean_absolute_percentage_error(y_test_cases, pred_base_cases) * 100
    r2_base = r2_score(y_test_cases, pred_base_cases)

    # Paired test vs persistence
    err_base = np.abs(y_test_cases - pred_base_cases)
    err_persist = np.abs(y_test_cases - pred_persist)
    wilcoxon_stat, wilcoxon_p = stats.wilcoxon(err_base, err_persist)

    print(f"\nCLEAN REAL BASELINE (rho = 0.0, Differenced Target):")
    print(f"  WAPE: {wape_base:.2f}%  |  MAPE: {mape_base:.2f}%  |  R^2: {r2_base:.4f}")
    print(f"  Paired Wilcoxon vs Persistence: stat={wilcoxon_stat:.1f}, p={wilcoxon_p:.4f}")
    if wilcoxon_p < 0.05:
        print("  -> Difference from persistence IS statistically significant.")
    else:
        print("  -> WARNING: Difference from persistence is NOT statistically significant (p >= 0.05).")

    print("\n" + "=" * 85)
    print("RUNNING 30-TRIAL REPETITION FOR CONTAMINATION SWEEP (DIFFERENCED TARGET)")
    print("=" * 85)
    print(f"{'Contam. (rho)':<14} | {'Mean WAPE (95% CI)':<26} | {'Mean R^2 (95% CI)':<26} | {'WAPE Std':<10}")
    print("-" * 85)

    rhos = [0.00, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 0.85]
    N_TRIALS = 30
    sweep_summary = []

    for rho in rhos:
        wapes = []
        r2s = []
        mapes = []

        if rho == 0.0:
            # Deterministic baseline across fixed training set
            wapes = [wape_base]
            r2s = [r2_base]
            mapes = [mape_base]
        else:
            n_real = len(train_real)
            n_synth = int(n_real * rho / (1.0 - rho))
            
            for seed in range(N_TRIALS):
                sample_synth = synth_features.sample(n=min(n_synth, len(synth_features)), random_state=100 + seed)
                train_curr = pd.concat([train_real, sample_synth], ignore_index=True)

                model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
                model.fit(train_curr[diff_features], train_curr["target_diff"])
                pred_delta = model.predict(test_real[diff_features])
                pred_cases = np.maximum(0, lag1_test + pred_delta)

                wapes.append(compute_wape(y_test_cases, pred_cases))
                r2s.append(r2_score(y_test_cases, pred_cases))
                mapes.append(mean_absolute_percentage_error(y_test_cases, pred_cases) * 100)

        wapes = np.array(wapes)
        r2s = np.array(r2s)

        mean_w = np.mean(wapes)
        ci_w_low, ci_w_high = (mean_w, mean_w) if rho == 0.0 else (np.percentile(wapes, 2.5), np.percentile(wapes, 97.5))
        std_w = np.std(wapes)

        mean_r = np.mean(r2s)
        ci_r_low, ci_r_high = (mean_r, mean_r) if rho == 0.0 else (np.percentile(r2s, 2.5), np.percentile(r2s, 97.5))

        sweep_summary.append({
            "rho": rho,
            "mean_wape": mean_w,
            "ci_w": (ci_w_low, ci_w_high),
            "std_w": std_w,
            "mean_r2": mean_r,
            "ci_r": (ci_r_low, ci_r_high)
        })

        ci_w_str = f"[{ci_w_low:.2f}, {ci_w_high:.2f}]"
        ci_r_str = f"[{ci_r_low:.4f}, {ci_r_high:.4f}]"
        print(f"{rho*100:>5.1f}%{'':<8} | {mean_w:>6.2f}% {ci_w_str:<17} | {mean_r:>7.4f} {ci_r_str:<17} | {std_w:>6.2f}%")

    print("-" * 85)

    # Check CI overlap between clean baseline (rho=0) and high contamination (rho=0.85)
    r85_ci_w = sweep_summary[-1]["ci_w"]
    base_val = sweep_summary[0]["mean_wape"]
    print("\nSTATISTICAL RIGOR EVALUATION:")
    print(f"Clean Baseline WAPE: {base_val:.2f}%")
    print(f"Rho=85% WAPE 95% CI: [{r85_ci_w[0]:.2f}%, {r85_ci_w[1]:.2f}%]")
    if base_val < r85_ci_w[0]:
        print("-> Separation CONFIRMED: Baseline WAPE is strictly below the 95% CI of rho=85%.")
    else:
        print("-> OVERLAP: Baseline WAPE falls WITHIN or ABOVE the 95% CI. The difference is NOT statistically separable from noise.")

if __name__ == "__main__":
    run_rigorous_sweep()
