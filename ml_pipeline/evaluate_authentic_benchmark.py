"""
ml_pipeline/evaluate_authentic_benchmark.py
Phase 2C-2: Statistical Evaluation & Estimator Selection on Clean Authentic Data.

Evaluates the deployed production forecaster artifact (forecast_cases_model.pkl)
with the verified inversion fix (np.expm1) against the Naive Persistence baseline (y_{t-1})
on canonical MoHFW/COVID19-India surveillance data.

Calculates:
  1. WAPE, MAPE, MAE, RMSE, R^2
  2. Cluster-Robust Diebold-Mariano test (Liang-Zeger, degrees of freedom = G - 1)
  3. Per-State Time Series Diebold-Mariano distribution
  4. Diagnostic Comparison against pooled 1D Newey-West HAC
"""

import os
import sys
import json
import math
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.predictors.forecast_predictor import ForecastPredictor

DATA_PATH = PROJECT_ROOT / "data" / "external_verified" / "authentic_covid_surveillance.csv"
RESULTS_DIR = PROJECT_ROOT / "paper_revision" / "results"
RESULTS_JSON = RESULTS_DIR / "authentic_forecast_evaluation.json"


def cluster_robust_dm(d: np.ndarray, clusters: np.ndarray) -> dict:
    """
    Cluster-robust Diebold-Mariano test (Liang-Zeger / Arellano cluster variance).
    d = loss_model - loss_baseline
    Negative d means model has lower loss (superior performance).
    """
    d = np.asarray(d, dtype=np.float64)
    clusters = np.asarray(clusters)
    n = len(d)
    d_bar = float(np.mean(d))
    unique_clusters = np.unique(clusters)
    G = len(unique_clusters)
    
    cluster_sums = np.array([np.sum(d[clusters == c]) for c in unique_clusters])
    v_cr = float(np.sum(cluster_sums ** 2) / (n ** 2))
    se_cr = math.sqrt(v_cr) if v_cr > 0 else 1e-12
    t_stat = d_bar / se_cr
    p_val = float(2.0 * stats.t.sf(abs(t_stat), df=G - 1))
    
    return {
        "t_stat": t_stat,
        "p_value": p_val,
        "se": se_cr,
        "mean_diff": d_bar,
        "n_clusters": G,
        "df": G - 1,
    }


def pooled_newey_west_dm(d: np.ndarray, h: int = 1) -> dict:
    """
    1D Newey-West HAC Diebold-Mariano (for diagnostic comparison showing why
    pooling interleaved panels into 1D is methodologically invalid).
    """
    d = np.asarray(d, dtype=np.float64)
    n = len(d)
    d_bar = float(np.mean(d))
    gamma_0 = float(np.mean((d - d_bar) ** 2))
    
    gamma_sum = 0.0
    bandwidth = h - 1
    for k in range(1, bandwidth + 1):
        weight = 1.0 - (k / (bandwidth + 1))
        gamma_k = float(np.mean((d[k:] - d_bar) * (d[:-k] - d_bar)))
        gamma_sum += 2.0 * weight * gamma_k
        
    var_d = (gamma_0 + gamma_sum) / n
    se_d = math.sqrt(var_d) if var_d > 0 else 1e-12
    hlnc = math.sqrt(max(0.0, (n + 1 - 2 * h + h * (h - 1) / n) / n))
    dm_stat = (d_bar / se_d) * hlnc
    p_val = float(2.0 * stats.t.sf(abs(dm_stat), df=n - 1))
    
    return {
        "dm_stat": dm_stat,
        "p_value": p_val,
        "se": se_d,
        "mean_diff": d_bar,
        "bandwidth": bandwidth,
    }


def evaluate_dataset_slice(df: pd.DataFrame, target_dates: list, period_name: str, predictor: ForecastPredictor):
    y_true = []
    y_pred_m = []
    y_pred_n = []
    clusters = []
    dates_list = []
    
    states = sorted(df["state"].unique())
    for state in states:
        state_df = df[df["state"] == state].sort_values("date").reset_index(drop=True)
        dates = state_df["date"].tolist()
        cases = state_df["confirmed_cases"].tolist()
        deaths = state_df["deaths"].tolist()
        
        for i, d in enumerate(dates):
            if d in target_dates:
                if i < 3:
                    continue
                history = [
                    (cases[i-3], deaths[i-3]),
                    (cases[i-2], deaths[i-2]),
                    (cases[i-1], deaths[i-1]),
                ]
                
                target_y = int(d[:4])
                target_m = int(d[5:7])
                prev_y = target_y - 1 if target_m == 1 else target_y
                prev_m = 12 if target_m == 1 else target_m - 1

                # Model inference via production predictor (which applies np.expm1)
                res = predictor.predict({
                    "disease": "COVID-19",
                    "state": state,
                    "history": history,
                    "months_ahead": 1,
                    "start_year_month": [prev_y, prev_m],
                })
                pred_cases = res["forecast"][0]["confirmed_cases"]
                naive_cases = cases[i-1] # persistence baseline
                
                y_true.append(cases[i])
                y_pred_m.append(pred_cases)
                y_pred_n.append(naive_cases)
                clusters.append(state)
                dates_list.append(d)
                
    y_true = np.array(y_true, dtype=np.float64)
    y_pred_m = np.array(y_pred_m, dtype=np.float64)
    y_pred_n = np.array(y_pred_n, dtype=np.float64)
    clusters = np.array(clusters)
    
    n = len(y_true)
    G = len(np.unique(clusters))
    
    # 1. Error metrics
    denom_wape = np.sum(np.abs(y_true))
    wape_m = float(np.sum(np.abs(y_true - y_pred_m)) / denom_wape * 100.0) if denom_wape > 0 else 0.0
    wape_n = float(np.sum(np.abs(y_true - y_pred_n)) / denom_wape * 100.0) if denom_wape > 0 else 0.0
    
    denom_mape = np.maximum(np.abs(y_true), 1.0)
    mape_m = float(np.mean(np.abs(y_true - y_pred_m) / denom_mape) * 100.0)
    mape_n = float(np.mean(np.abs(y_true - y_pred_n) / denom_mape) * 100.0)
    
    mae_m = float(np.mean(np.abs(y_true - y_pred_m)))
    mae_n = float(np.mean(np.abs(y_true - y_pred_n)))
    
    rmse_m = float(np.sqrt(np.mean((y_true - y_pred_m) ** 2)))
    rmse_n = float(np.sqrt(np.mean((y_true - y_pred_n) ** 2)))
    
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2_m = float(1.0 - (np.sum((y_true - y_pred_m) ** 2) / ss_tot)) if ss_tot > 0 else 0.0
    r2_n = float(1.0 - (np.sum((y_true - y_pred_n) ** 2) / ss_tot)) if ss_tot > 0 else 0.0
    
    # 2. Differentials
    e_m = y_true - y_pred_m
    e_n = y_true - y_pred_n
    d_sq = (e_m ** 2) - (e_n ** 2)
    d_abs = np.abs(e_m) - np.abs(e_n)
    
    # 3. Cluster-robust DM tests
    dm_cr_sq = cluster_robust_dm(d_sq, clusters)
    dm_cr_abs = cluster_robust_dm(d_abs, clusters)
    
    # 4. 1D Pooled Newey-West DM (methodologically flawed legacy baseline)
    dm_pool_sq = pooled_newey_west_dm(d_sq, h=1)
    dm_pool_abs = pooled_newey_west_dm(d_abs, h=1)
    
    # 5. State-level granularity
    state_wins_sq = 0
    state_wins_abs = 0
    state_metrics = {}
    for c in np.unique(clusters):
        c_mask = (clusters == c)
        c_true = y_true[c_mask]
        c_m = y_pred_m[c_mask]
        c_n = y_pred_n[c_mask]
        
        c_wape_m = float(np.sum(np.abs(c_true - c_m)) / np.sum(np.abs(c_true)) * 100.0) if np.sum(c_true) > 0 else 0.0
        c_wape_n = float(np.sum(np.abs(c_true - c_n)) / np.sum(np.abs(c_true)) * 100.0) if np.sum(c_true) > 0 else 0.0
        
        c_d_sq = np.sum(d_sq[c_mask])
        c_d_abs = np.sum(d_abs[c_mask])
        if c_d_sq < 0:
            state_wins_sq += 1
        if c_d_abs < 0:
            state_wins_abs += 1
            
        state_metrics[c] = {
            "wape_model": c_wape_m,
            "wape_naive": c_wape_n,
            "sum_d_sq": float(c_d_sq),
            "sum_d_abs": float(c_d_abs),
            "superior_sq": "Model" if c_d_sq < 0 else "Naive",
            "superior_abs": "Model" if c_d_abs < 0 else "Naive",
        }
        
    res = {
        "period_name": period_name,
        "n_windows": n,
        "n_states": G,
        "model_metrics": {
            "wape": wape_m,
            "mape": mape_m,
            "mae": mae_m,
            "rmse": rmse_m,
            "r2": r2_m,
        },
        "naive_metrics": {
            "wape": wape_n,
            "mape": mape_n,
            "mae": mae_n,
            "rmse": rmse_n,
            "r2": r2_n,
        },
        "cluster_robust_dm_squared": dm_cr_sq,
        "cluster_robust_dm_absolute": dm_cr_abs,
        "pooled_newey_west_dm_squared": dm_pool_sq,
        "pooled_newey_west_dm_absolute": dm_pool_abs,
        "state_breakdown": {
            "states_where_model_beats_naive_squared": state_wins_sq,
            "states_where_model_beats_naive_absolute": state_wins_abs,
            "pct_states_model_superior_squared": float(state_wins_sq / G * 100.0),
            "pct_states_model_superior_absolute": float(state_wins_abs / G * 100.0),
            "per_state": state_metrics,
        }
    }
    
    # Print formatted output table
    print("=" * 80)
    print(f"BENCHMARK RESULTS: {period_name}")
    print(f"Sample Size: {n} windows across {G} states | Target dates: {target_dates[0]} to {target_dates[-1]}")
    print("=" * 80)
    print(f"{'Metric':<25} | {'Deployed Model (expm1)':<22} | {'Naive Persistence (y_t-1)':<24} | {'Superior'}")
    print("-" * 80)
    print(f"{'WAPE (%)':<25} | {wape_m:<22.2f} | {wape_n:<24.2f} | {'Model' if wape_m < wape_n else 'Naive'}")
    print(f"{'MAPE (%)':<25} | {mape_m:<22.2f} | {mape_n:<24.2f} | {'Model' if mape_m < mape_n else 'Naive'}")
    print(f"{'MAE (cases)':<25} | {mae_m:<22,.1f} | {mae_n:<24,.1f} | {'Model' if mae_m < mae_n else 'Naive'}")
    print(f"{'RMSE (cases)':<25} | {rmse_m:<22,.1f} | {rmse_n:<24,.1f} | {'Model' if rmse_m < rmse_n else 'Naive'}")
    print(f"{'R^2':<25} | {r2_m:<22.4f} | {r2_n:<24.4f} | {'Model' if r2_m > r2_n else 'Naive'}")
    print("-" * 80)
    print(f"Cluster-Robust DM (Squared Loss):  t = {dm_cr_sq['t_stat']:+.4f}, p = {dm_cr_sq['p_value']:.4f} (df={dm_cr_sq['df']})")
    print(f"Cluster-Robust DM (Absolute Loss): t = {dm_cr_abs['t_stat']:+.4f}, p = {dm_cr_abs['p_value']:.4f} (df={dm_cr_abs['df']})")
    print(f"Pooled 1D Newey-West (Squared):    t = {dm_pool_sq['dm_stat']:+.4f}, p = {dm_pool_sq['p_value']:.4f} [Methodologically flawed]")
    print(f"State-level Superiority:           Squared: {state_wins_sq}/{G} states ({state_wins_sq/G*100:.1f}%) | Absolute: {state_wins_abs}/{G} states ({state_wins_abs/G*100:.1f}%)")
    print("=" * 80 + "\n")
    
    return res


def run_evaluation():
    print("Loading authentic COVID-19 surveillance dataset...")
    df = pd.read_csv(DATA_PATH)
    
    print("Initializing deployed ForecastPredictor with expm1...")
    predictor = ForecastPredictor()
    predictor.load_model()
    
    # Target periods
    # 1. Delta Surge (Apr-Jul 2021): 4 months x 30 states = 120 windows
    delta_dates = ["2021-04-01", "2021-05-01", "2021-06-01", "2021-07-01"]
    
    # 2. Wave 1 Surge (Jun 2020-Feb 2021): 9 months x 30 states = 270 windows
    w1_dates = [f"2020-{m:02d}-01" for m in range(6, 13)] + ["2021-01-01", "2021-02-01"]
    
    # 3. Full Authentic Surveillance (Jun 2020-Oct 2021): 17 months x 30 states = 510 windows
    full_dates = sorted(df["date"].unique())[3:]
    
    results = {
        "metadata": {
            "source_data": str(DATA_PATH),
            "model_evaluated": "forecast_cases_model.pkl (with production expm1 inversion)",
            "baseline": "Naive Persistence (y_{t-1})",
            "eval_script": "ml_pipeline/evaluate_authentic_benchmark.py",
            "timestamp": "2026-09-20",
        },
        "periods": {
            "delta_surge": evaluate_dataset_slice(df, delta_dates, "Delta Wave Surge (Apr 2021 - Jul 2021)", predictor),
            "wave_1": evaluate_dataset_slice(df, w1_dates, "Wave 1 Surge (Jun 2020 - Feb 2021)", predictor),
            "full_surveillance": evaluate_dataset_slice(df, full_dates, "Full Authentic Surveillance (Jun 2020 - Oct 2021)", predictor),
        }
    }
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_JSON, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results successfully saved to: {RESULTS_JSON}")


if __name__ == "__main__":
    run_evaluation()
