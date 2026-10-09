"""
generate_final_paper_results.py
Single consolidated, authoritative script generating ALL empirical results for the revised paper:
1. Calibrated Baselines on Delta Wave (Persistence, RidgeCV, Clean XGBoost, Augmented XGBoost)
2. Paired Wilcoxon Signed-Rank Test (Clean XGBoost vs Persistence)
3. 30-Trial Uncertainty-Aware Contamination Sweep (rhos: 0 to 85%, Mean + 95% CIs)
4. Saturation Check (Pearson r, MAE, and % diff between rho=20% and rho=85%)
5. Outputs saved to paper_revision/results/authoritative_results.json
"""

import os
import json
import math
import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_percentage_error, r2_score
from scipy import stats

def compute_wape(y_true, y_pred):
    denom = np.sum(y_true)
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)

def main():
    print("=" * 80)
    print("RUNNING CONSOLIDATED END-TO-END BENCHMARK & REPRODUCIBILITY HARNESS")
    print("=" * 80)

    os.makedirs("paper_revision/results", exist_ok=True)

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
                    "date": str(row["date"].date()),
                    "state": state,
                    "month_sin": math.sin(2 * math.pi * m / 12),
                    "month_cos": math.cos(2 * math.pi * m / 12),
                    "lag_1_cases": float(lag1["confirmed_cases"]),
                    "lag_2_cases": float(lag2["confirmed_cases"]),
                    "lag_3_cases": float(lag3["confirmed_cases"]),
                    "cases_ma3": float((lag1["confirmed_cases"] + lag2["confirmed_cases"] + lag3["confirmed_cases"]) / 3.0),
                    "lag_1_diff": float(lag1["confirmed_cases"] - lag2["confirmed_cases"]),
                    "lag_2_diff": float(lag2["confirmed_cases"] - lag3["confirmed_cases"]),
                    "target_cases": float(row["confirmed_cases"]),
                    "target_diff": float(row["confirmed_cases"] - lag1["confirmed_cases"]),
                })
        return pd.DataFrame(records)

    real_features = build_dataset(real_cov)
    synth_features = build_dataset(synth_cov)

    train_real = real_features[real_features["date"] < "2021-04-01"].copy()
    test_real = real_features[real_features["date"] >= "2021-04-01"].copy()

    diff_features = ["month_sin", "month_cos", "lag_1_diff", "lag_2_diff", "lag_1_cases", "cases_ma3"]
    y_test = test_real["target_cases"].values
    lag1_test = test_real["lag_1_cases"].values

    # 1. BASELINE BENCHMARKS
    print("\n--- 1. EVALUATING BASELINES ON DELTA TEST SET (N=120) ---")
    
    # 1a. Persistence
    pred_persist = lag1_test
    wape_persist = compute_wape(y_test, pred_persist)
    mape_persist = float(mean_absolute_percentage_error(y_test, pred_persist) * 100)
    r2_persist = float(r2_score(y_test, pred_persist))

    # 1b. RidgeCV
    ridge = RidgeCV(alphas=[0.01, 0.1, 1.0, 10.0, 100.0])
    ridge.fit(train_real[diff_features], train_real["target_diff"])
    pred_ridge_diff = ridge.predict(test_real[diff_features])
    pred_ridge = np.maximum(0, lag1_test + pred_ridge_diff)
    wape_ridge = compute_wape(y_test, pred_ridge)
    mape_ridge = float(mean_absolute_percentage_error(y_test, pred_ridge) * 100)
    r2_ridge = float(r2_score(y_test, pred_ridge))

    # 1c. Auto-ARIMA per-state rolling forecast (AIC-selected orders)
    from statsmodels.tsa.arima.model import ARIMA
    candidate_orders = [(1, 0, 0), (0, 1, 1), (1, 1, 0)]
    y_pred_arima = []
    for state in real_cov["state"].unique():
        s_df = real_cov[real_cov["state"] == state].sort_values("date").reset_index(drop=True)
        dates = s_df["date"].dt.strftime("%Y-%m-%d").values
        cases = s_df["confirmed_cases"].values
        for i in range(len(dates)):
            if dates[i] >= "2021-04-01":
                history = cases[:i]
                best_aic = float("inf")
                best_pred = history[-1]
                for order in candidate_orders:
                    try:
                        res = ARIMA(history, order=order).fit()
                        if res.aic < best_aic:
                            best_aic = res.aic
                            best_pred = res.forecast(steps=1)[0]
                    except Exception:
                        pass
                y_pred_arima.append(max(0, float(best_pred)))
    pred_arima = np.array(y_pred_arima)
    wape_arima = compute_wape(y_test, pred_arima)
    mape_arima = float(mean_absolute_percentage_error(y_test, pred_arima) * 100)
    r2_arima = float(r2_score(y_test, pred_arima))

    # 1d. Clean Real XGBoost (rho = 0.0)
    xgb_clean = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_clean.fit(train_real[diff_features], train_real["target_diff"])
    pred_clean_diff = xgb_clean.predict(test_real[diff_features])
    pred_clean = np.maximum(0, lag1_test + pred_clean_diff)
    wape_clean = compute_wape(y_test, pred_clean)
    mape_clean = float(mean_absolute_percentage_error(y_test, pred_clean) * 100)
    r2_clean = float(r2_score(y_test, pred_clean))

    # 1e. Augmented XGBoost (rho = 0.50, seed 142)
    n_real = len(train_real)
    n_synth_50 = int(n_real * 0.50 / 0.50)
    s50 = synth_features.sample(n=min(n_synth_50, len(synth_features)), random_state=142)
    t50 = pd.concat([train_real, s50], ignore_index=True)
    xgb_50 = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    xgb_50.fit(t50[diff_features], t50["target_diff"])
    pred_50_diff = xgb_50.predict(test_real[diff_features])
    pred_50 = np.maximum(0, lag1_test + pred_50_diff)
    wape_50 = compute_wape(y_test, pred_50)
    mape_50 = float(mean_absolute_percentage_error(y_test, pred_50) * 100)
    r2_50 = float(r2_score(y_test, pred_50))

    # 2. STATISTICAL SIGNIFICANCE TESTS (Clean XGBoost vs Persistence)
    err_clean = np.abs(y_test - pred_clean)
    err_persist = np.abs(y_test - pred_persist)
    wilcox_stat, wilcox_p = stats.wilcoxon(err_clean, err_persist)

    # State-clustered analysis (N=30 clusters)
    test_eval = test_real.copy()
    test_eval["err_clean"] = err_clean
    test_eval["err_persist"] = err_persist
    state_agg = test_eval.groupby("state")[["err_clean", "err_persist"]].mean()
    w_clust_stat, w_clust_p = stats.wilcoxon(state_agg["err_clean"], state_agg["err_persist"])

    # State-cluster block bootstrap (B=5000)
    np.random.seed(42)
    state_diffs = (state_agg["err_persist"] - state_agg["err_clean"]).values
    boot_means = [np.mean(np.random.choice(state_diffs, size=len(state_diffs), replace=True)) for _ in range(5000)]
    ci_l, ci_u = np.percentile(boot_means, [2.5, 97.5])
    p_boot = float(np.mean(np.array(boot_means) <= 0))

    print(f"Persistence: WAPE={wape_persist:.2f}%, MAPE={mape_persist:.2f}%, R^2={r2_persist:.4f}")
    print(f"RidgeCV:     WAPE={wape_ridge:.2f}%, MAPE={mape_ridge:.2f}%, R^2={r2_ridge:.4f}")
    print(f"Auto-ARIMA:  WAPE={wape_arima:.2f}%, MAPE={mape_arima:.2f}%, R^2={r2_arima:.4f}")
    print(f"Clean XGB:   WAPE={wape_clean:.2f}%, MAPE={mape_clean:.2f}%, R^2={r2_clean:.4f}")
    print(f"Aug XGB 50%: WAPE={wape_50:.2f}%, MAPE={mape_50:.2f}%, R^2={r2_50:.4f}")
    print(f"Pooled Wilcoxon (N=120): W={wilcox_stat:.1f}, p={wilcox_p:.4f}")
    print(f"State-Clustered Wilcoxon (N=30): W={w_clust_stat:.1f}, p={w_clust_p:.4f}")
    print(f"Cluster Bootstrap (B=5000): 95% CI=[{ci_l:.1f}, {ci_u:.1f}], p={p_boot:.4f}")

    # 3. 30-TRIAL CONTAMINATION SWEEP
    print("\n--- 2. RUNNING 30-TRIAL CONTAMINATION SWEEP ---")
    rhos = [0.00, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70, 0.85]
    N_TRIALS = 30
    sweep_table = []

    for rho in rhos:
        if rho == 0.0:
            sweep_table.append({
                "rho": rho,
                "mean_wape": wape_clean,
                "ci_wape_low": wape_clean,
                "ci_wape_high": wape_clean,
                "std_wape": 0.0,
                "mean_r2": r2_clean,
                "ci_r2_low": r2_clean,
                "ci_r2_high": r2_clean,
                "mean_mape": mape_clean
            })
            continue

        w_list, r_list, m_list = [], [], []
        n_synth = int(n_real * rho / (1.0 - rho))

        for seed in range(N_TRIALS):
            sample_s = synth_features.sample(n=min(n_synth, len(synth_features)), random_state=100 + seed)
            train_c = pd.concat([train_real, sample_s], ignore_index=True)
            model = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
            model.fit(train_c[diff_features], train_c["target_diff"])
            pred = np.maximum(0, lag1_test + model.predict(test_real[diff_features]))
            w_list.append(compute_wape(y_test, pred))
            r_list.append(float(r2_score(y_test, pred)))
            m_list.append(float(mean_absolute_percentage_error(y_test, pred) * 100))

        sweep_table.append({
            "rho": rho,
            "mean_wape": float(np.mean(w_list)),
            "ci_wape_low": float(np.percentile(w_list, 2.5)),
            "ci_wape_high": float(np.percentile(w_list, 97.5)),
            "std_wape": float(np.std(w_list)),
            "mean_r2": float(np.mean(r_list)),
            "ci_r2_low": float(np.percentile(r_list, 2.5)),
            "ci_r2_high": float(np.percentile(r_list, 97.5)),
            "mean_mape": float(np.mean(m_list))
        })
        print(f"rho={rho*100:>4.1f}%: Mean WAPE={np.mean(w_list):.2f}% [{np.percentile(w_list, 2.5):.2f}, {np.percentile(w_list, 97.5):.2f}], R^2={np.mean(r_list):.4f}")

    # 4. SATURATION CHECK (rho=20% vs rho=85%)
    print("\n--- 3. SATURATION CHECK (rho=20% vs rho=85%) ---")
    n_s20 = int(n_real * 0.20 / 0.80)
    s20 = synth_features.sample(n=min(n_s20, len(synth_features)), random_state=142)
    t20 = pd.concat([train_real, s20], ignore_index=True)
    m20 = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    m20.fit(t20[diff_features], t20["target_diff"])
    p20 = np.maximum(0, lag1_test + m20.predict(test_real[diff_features]))

    n_s85 = int(n_real * 0.85 / 0.15)
    s85 = synth_features.sample(n=min(n_s85, len(synth_features)), random_state=142)
    t85 = pd.concat([train_real, s85], ignore_index=True)
    m85 = XGBRegressor(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=42)
    m85.fit(t85[diff_features], t85["target_diff"])
    p85 = np.maximum(0, lag1_test + m85.predict(test_real[diff_features]))

    r_sat, p_sat = stats.pearsonr(p20, p85)
    mae_diff = float(np.mean(np.abs(p20 - p85)))
    rel_diff = float(mae_diff / np.mean(y_test) * 100)

    print(f"Pearson r={r_sat:.4f}, p={p_sat:.2e}, MAE diff={mae_diff:.1f}, Rel diff={rel_diff:.2f}%")

    final_payload = {
        "baselines": {
            "persistence": {"wape": wape_persist, "mape": mape_persist, "r2": r2_persist},
            "ridge_cv": {"wape": wape_ridge, "mape": mape_ridge, "r2": r2_ridge},
            "auto_arima": {"wape": wape_arima, "mape": mape_arima, "r2": r2_arima},
            "xgb_clean": {"wape": wape_clean, "mape": mape_clean, "r2": r2_clean},
            "xgb_aug_50": {"wape": wape_50, "mape": mape_50, "r2": r2_50}
        },
        "statistical_tests": {
            "pooled_wilcoxon": {"statistic": float(wilcox_stat), "p_value": float(wilcox_p), "n": 120},
            "state_clustered_wilcoxon": {"statistic": float(w_clust_stat), "p_value": float(w_clust_p), "clusters": 30},
            "state_cluster_bootstrap": {"mean_delta": float(np.mean(boot_means)), "ci_95_low": float(ci_l), "ci_95_high": float(ci_u), "p_value": p_boot, "b": 5000}
        },
        "wilcoxon": {"statistic": float(wilcox_stat), "p_value": float(wilcox_p)},
        "sweep": sweep_table,
        "saturation": {
            "pearson_r": float(r_sat),
            "p_value": float(p_sat),
            "mae_diff": mae_diff,
            "rel_diff_pct": rel_diff
        }
    }

    with open("paper_revision/results/authoritative_results.json", "w") as f:
        json.dump(final_payload, f, indent=2)

    print("\nSAVED AUTHORITATIVE RESULTS TO paper_revision/results/authoritative_results.json")

if __name__ == "__main__":
    main()
