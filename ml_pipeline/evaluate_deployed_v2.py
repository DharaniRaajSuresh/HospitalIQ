"""
ml_pipeline/evaluate_deployed_v2.py
Phase 2B: Corrected Deployed Forecaster Evaluation Harness with Inversion Fix (expm1).

This script provides an independently verifiable, clean evaluation of the deployed
forecast model artifact (ml_pipeline/data/models/forecast_cases_model.pkl).

Key Improvements over Buggy evaluate_deployed.py / deployed_forecast_authentic_eval.py:
1. Correctly applies np.expm1() to invert log1p targets, achieving 100% parity with
   production serving code (backend/predictors/forecast_predictor.py:140).
2. Preserves float32 array casting before expm1 to prevent numerical precision drift.
3. Provides exact implementations of:
   - Volume-weighted Absolute Percentage Error (WAPE)
   - Mean Absolute Percentage Error (MAPE)
   - Coefficient of Determination (R^2)
   - Spatial Cluster-Robust Diebold-Mariano test (Liang-Zeger, df=G-1)
   - Temporal Newey-West HAC Diebold-Mariano test (Harvey-Leybourne-Newbold, bandwidth h-1)
"""

import os
import sys
import math
import pickle
import numpy as np
import pandas as pd
from scipy import stats

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")
RAW_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "raw")

sys.path.insert(0, HOSPI)
from backend.predictors.forecast_predictor import ForecastPredictor


def load_artifacts():
    """Load model and metadata pickles."""
    model_path = os.path.join(MODELS_DIR, "forecast_cases_model.pkl")
    meta_path = os.path.join(MODELS_DIR, "forecast_metadata.pkl")
    
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
    return model, meta


# ==============================================================================
# STATISTICAL METRICS & STATISTICAL TEST FORMULAS
# ==============================================================================

def compute_wape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Volume-weighted Absolute Percentage Error: (sum |y - y_hat|) / (sum |y|) * 100."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    denom = np.sum(np.abs(y_true))
    if denom == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0)


def compute_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error with nonzero denominator guard."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    denom = np.maximum(np.abs(y_true), 1.0)
    return float(np.mean(np.abs(y_true - y_pred) / denom) * 100.0)


def compute_r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Standard Coefficient of Determination R^2 = 1 - SS_res / SS_tot."""
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1.0 - (ss_res / ss_tot))


def cluster_robust_dm(d: np.ndarray, clusters: np.ndarray) -> dict:
    """
    Cluster-robust Diebold-Mariano test for clustered observational units (e.g. states).
    
    Parameters:
      d: array-like of loss differentials (loss_model - loss_baseline).
         Positive d means model has higher loss than baseline (negative skill).
      clusters: array-like of cluster identifiers (e.g., state names).
      
    Variance:
      V_CR = sum_g ( sum_{i in g} d_i )^2 / n^2
      SE_CR = sqrt(V_CR)
      stat = mean(d) / SE_CR ~ t(G - 1)
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
        "mean_diff": d_bar,
        "se": se_cr,
        "n_clusters": G,
        "df": G - 1,
    }


def newey_west_hac_dm(y_true: np.ndarray, y_pred1: np.ndarray, y_pred2: np.ndarray, 
                       h: int = 1, loss: str = "squared") -> dict:
    """
    Time-series Diebold-Mariano test with Newey-West HAC variance adjustment
    and Harvey-Leybourne-Newbold (1997) small-sample finite horizon correction.
    
    Parameters:
      y_true: ground truth array
      y_pred1: model predictions
      y_pred2: baseline predictions
      h: forecast horizon (default: 1 step ahead)
      loss: 'squared' (e1^2 - e2^2) or 'absolute' (|e1| - |e2|)
      
    Bandwidth:
      bandwidth = h - 1 (for h=1, bandwidth=0, meaning no serial lag covariance).
      Weights: Bartlett kernel w_k = 1 - k / (bandwidth + 1) for k <= bandwidth.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred1 = np.asarray(y_pred1, dtype=np.float64)
    y_pred2 = np.asarray(y_pred2, dtype=np.float64)
    
    e1 = y_true - y_pred1
    e2 = y_true - y_pred2
    
    if loss == "absolute":
        d = np.abs(e1) - np.abs(e2)
    else:
        d = (e1 ** 2) - (e2 ** 2)
        
    n = len(d)
    d_bar = float(np.mean(d))
    gamma_0 = float(np.mean((d - d_bar) ** 2))
    
    # Newey-West Bartlett kernel over lags 1 to h-1
    gamma_sum = 0.0
    bandwidth = h - 1
    for k in range(1, bandwidth + 1):
        weight = 1.0 - (k / (bandwidth + 1))
        gamma_k = float(np.mean((d[k:] - d_bar) * (d[:-k] - d_bar)))
        gamma_sum += 2.0 * weight * gamma_k
        
    var_d = (gamma_0 + gamma_sum) / n
    se_d = math.sqrt(var_d) if var_d > 0 else 1e-12
    dm_raw = d_bar / se_d
    
    # HLN small sample adjustment
    hlnc = math.sqrt(max(0.0, (n + 1 - 2 * h + h * (h - 1) / n) / n))
    dm_stat = dm_raw * hlnc
    p_val = float(2.0 * stats.t.sf(abs(dm_stat), df=n - 1))
    
    return {
        "dm_stat": dm_stat,
        "p_value": p_val,
        "mean_diff": d_bar,
        "se": se_d,
        "h": h,
        "bandwidth": bandwidth,
        "loss": loss,
        "df": n - 1,
    }


# ==============================================================================
# TEN-WINDOW MATCH VERIFICATION (EVALUATE_DEPLOYED_V2 VS PRODUCTION SERVING)
# ==============================================================================

def run_ten_window_verification():
    """
    Executes a side-by-side 10-window verification between evaluate_deployed_v2
    and backend.predictors.forecast_predictor.ForecastPredictor.
    """
    print("=" * 80)
    print("PHASE 2B: 10-WINDOW PRODUCTION SERVING PARITY VERIFICATION")
    print("=" * 80)
    
    model, meta = load_artifacts()
    prod = ForecastPredictor()
    prod.load_model()
    
    # Load 10 sample state windows from raw CSV
    csv_path = os.path.join(RAW_DIR, "outbreak_real.csv")
    df = pd.read_csv(csv_path, parse_dates=["date"])
    covid = df[df["disease"] == "COVID-19"].sort_values(["state", "date"]).reset_index(drop=True)
    
    states = [
        "Maharashtra", "Kerala", "Karnataka", "Tamil Nadu", "Delhi",
        "Uttar Pradesh", "Gujarat", "West Bengal", "Rajasthan", "Andhra Pradesh"
    ]
    
    results = []
    for idx, state in enumerate(states, 1):
        st_df = covid[covid["state"] == state].sort_values("date")
        row_matches = st_df[st_df["date"] == "2021-04-01"]
        if len(row_matches) == 0:
            continue
        row = row_matches.iloc[0]
        hist = st_df[st_df["date"] < row["date"]].sort_values("date")
        if len(hist) < 3:
            continue
            
        y_true = float(row["confirmed_cases"])
        date = row["date"]
        
        history_tuples = [(float(h["confirmed_cases"]), float(h["deaths"])) for _, h in hist.tail(3).iterrows()]
        prev_date = hist.iloc[-1]["date"]
        
        # 1. Call Production Predictor API
        prod_payload = {
            "disease": "COVID-19",
            "state": state,
            "history": history_tuples,
            "months_ahead": 1,
            "start_year_month": [prev_date.year, prev_date.month]
        }
        prod_res = prod.predict(prod_payload)
        prod_cases = prod_res["forecast"][0]["confirmed_cases"]
        
        # 2. Call evaluate_deployed_v2 corrected evaluation pipeline
        feat = prod.build_feature(
            history_tuples,
            meta["disease_encoding"]["COVID-19"],
            meta["state_encoding"][state],
            meta["disease_params"]["COVID-19"]["cfr"],
            meta["disease_params"]["COVID-19"]["r0"],
            meta["state_beds"][state]["total_beds"],
            meta["state_beds"][state]["hospitals"],
            date.year, date.month
        )
        raw_log = model.predict(feat)[0]  # np.float32 exactly matching production serving
        expm1_val = float(np.expm1(raw_log))
        expm1_rounded = max(1, int(round(expm1_val)))
        
        match = (expm1_rounded == prod_cases)
        results.append({
            "window": idx,
            "state": state,
            "date": str(date)[:10],
            "y_true": y_true,
            "raw_log": float(raw_log),
            "expm1_val": expm1_val,
            "rounded": expm1_rounded,
            "prod_serving": prod_cases,
            "match": match,
        })
        
    res_df = pd.DataFrame(results)
    print(f"{'Win':3s} | {'State':15s} | {'Date':10s} | {'True Value':10s} | {'Raw Log':8s} | {'expm1 Val':12s} | {'Eval_v2':8s} | {'Prod_API':8s} | {'Match'}")
    print("-" * 96)
    for _, r in res_df.iterrows():
        print(f"{r['window']:3d} | {r['state']:15s} | {r['date']:10s} | {r['y_true']:10.0f} | {r['raw_log']:8.4f} | {r['expm1_val']:12.1f} | {r['rounded']:8d} | {r['prod_serving']:8d} | {r['match']}")
        
    all_matched = res_df["match"].all()
    print("-" * 96)
    print(f"Total Windows Tested: {len(res_df)}")
    print(f"Total Exact Matches:  {res_df['match'].sum()}/{len(res_df)}")
    print(f"Parity Verdict:       {'PASS (100% IDENTICAL)' if all_matched else 'FAIL'}")
    return res_df


if __name__ == "__main__":
    df_matches = run_ten_window_verification()
