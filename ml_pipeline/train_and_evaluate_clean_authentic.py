"""
ml_pipeline/train_and_evaluate_clean_authentic.py
Controlled Evaluation: Clean Retrained XGBoost vs Deployed Artifact vs Naive Persistence.

Addresses user audit requirements:
1. Retrains a clean XGBoost model strictly on authentic pre-Delta data (Wave 1: Jun 2020 - Mar 2021).
2. Directly compares:
   - Clean Retrained Model (trained on authentic scale)
   - Original Deployed Artifact (trained on inflated synthetic data)
   - Naive Persistence Baseline (y_{t-1})
3. Evaluates out-of-sample on Delta Wave (Apr 2021 - Jul 2021, N=120) and Full Out-of-Sample (Apr - Oct 2021, N=210).
4. Computes Cluster-Robust DM (df=29) and R^2.
"""

import os
import sys
import math
import pickle
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from xgboost import XGBRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.predictors.forecast_predictor import ForecastPredictor

DATA_PATH = PROJECT_ROOT / "data" / "external_verified" / "authentic_covid_surveillance.csv"
MODELS_DIR = PROJECT_ROOT / "ml_pipeline" / "data" / "models"
OUTPUT_MODEL_PATH = MODELS_DIR / "clean_authentic_forecast_cases_model.pkl"
RESULTS_JSON = PROJECT_ROOT / "paper_revision" / "results" / "clean_vs_deployed_forecast_evaluation.json"


def cluster_robust_dm(d: np.ndarray, clusters: np.ndarray) -> dict:
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


def compute_metrics(y_true, y_pred):
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)
    
    denom_wape = np.sum(np.abs(y_true))
    wape = float(np.sum(np.abs(y_true - y_pred)) / denom_wape * 100.0) if denom_wape > 0 else 0.0
    
    denom_mape = np.maximum(np.abs(y_true), 1.0)
    mape = float(np.mean(np.abs(y_true - y_pred) / denom_mape) * 100.0)
    
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1.0 - (np.sum((y_true - y_pred) ** 2) / ss_tot)) if ss_tot > 0 else 0.0
    
    return {"wape": wape, "mape": mape, "mae": mae, "rmse": rmse, "r2": r2}


def build_dataset():
    df = pd.read_csv(DATA_PATH)
    meta_path = MODELS_DIR / "forecast_metadata.pkl"
    with open(meta_path, "rb") as f:
        meta = pickle.load(f)
        
    records = []
    feature_cols = meta["feature_cols"]
    
    for state in sorted(df["state"].unique()):
        sdf = df[df["state"] == state].sort_values("date").reset_index(drop=True)
        dates = sdf["date"].tolist()
        cases = sdf["confirmed_cases"].tolist()
        deaths = sdf["deaths"].tolist()
        
        cap = meta.get("state_beds", {}).get(state, {"total_beds": 1000, "hospitals": 10})
        s_enc = meta.get("state_encoding", {}).get(state, 0)
        d_enc = meta.get("disease_encoding", {}).get("COVID-19", 0)
        dp = meta.get("disease_params", {}).get("COVID-19", {})
        d_cfr = dp.get("cfr", 0.57)
        d_r0 = dp.get("r0", 0.95)
        
        for i in range(3, len(dates)):
            d = dates[i]
            year = int(d[:4])
            month = int(d[5:7])
            
            m_sin = math.sin(2 * math.pi * month / 12)
            m_cos = math.cos(2 * math.pi * month / 12)
            y_norm = (year - 2017) / 15
            
            lag1_c = cases[i-1]
            lag2_c = cases[i-2]
            lag3_c = cases[i-3]
            lag1_d = deaths[i-1]
            lag2_d = deaths[i-2]
            
            ma3 = (lag1_c + lag2_c + lag3_c) / 3
            growth = (lag1_c - lag2_c) / max(lag2_c, 1)
            
            feat = {
                "date": d,
                "state": state,
                "month_sin": m_sin,
                "month_cos": m_cos,
                "year_normalized": y_norm,
                "lag_1_cases": lag1_c,
                "lag_2_cases": lag2_c,
                "lag_3_cases": lag3_c,
                "lag_1_deaths": lag1_d,
                "lag_2_deaths": lag2_d,
                "cases_ma3": ma3,
                "cases_growth": growth,
                "disease_cfr": d_cfr,
                "disease_r0": d_r0,
                "state_beds": cap["total_beds"],
                "state_hospitals": cap["hospitals"],
                "disease_enc": d_enc,
                "state_enc": s_enc,
                "target_cases": cases[i],
                "naive_cases": lag1_c,
            }
            records.append(feat)
            
    df_all = pd.DataFrame(records)
    return df_all, feature_cols, meta


def train_clean_model(df_train, feature_cols):
    X_train = df_train[feature_cols].values
    y_train = np.log1p(df_train["target_cases"].values)
    
    # Train XGBoost with matching architecture
    model = XGBRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        colsample_bytree=0.7,
        reg_alpha=0.1,
        reg_lambda=5.0,
        random_state=42,
        n_jobs=-1,
        objective="reg:squarederror"
    )
    model.fit(X_train, y_train)
    return model


def evaluate_split(df_test, clean_model, deployed_predictor, feature_cols, split_name):
    y_true = df_test["target_cases"].values
    y_naive = df_test["naive_cases"].values
    clusters = df_test["state"].values
    
    # 1. Clean model predictions
    X_test = df_test[feature_cols].values
    raw_clean_pred = clean_model.predict(X_test)
    y_clean = np.expm1(raw_clean_pred)
    y_clean = np.maximum(1.0, np.round(y_clean))
    
    # 2. Deployed original artifact predictions
    y_deployed = []
    for _, row in df_test.iterrows():
        d = row["date"]
        target_y = int(d[:4])
        target_m = int(d[5:7])
        prev_y = target_y - 1 if target_m == 1 else target_y
        prev_m = 12 if target_m == 1 else target_m - 1
        
        history = [
            (row["lag_3_cases"], 0),
            (row["lag_2_cases"], row["lag_2_deaths"]),
            (row["lag_1_cases"], row["lag_1_deaths"]),
        ]
        res = deployed_predictor.predict({
            "disease": "COVID-19",
            "state": row["state"],
            "history": history,
            "months_ahead": 1,
            "start_year_month": [prev_y, prev_m],
        })
        y_deployed.append(res["forecast"][0]["confirmed_cases"])
        
    y_deployed = np.array(y_deployed, dtype=np.float64)
    
    m_clean = compute_metrics(y_true, y_clean)
    m_deployed = compute_metrics(y_true, y_deployed)
    m_naive = compute_metrics(y_true, y_naive)
    
    # Differentials (Model - Baseline)
    # Negative means Model has lower error
    e_clean = y_true - y_clean
    e_dep = y_true - y_deployed
    e_naive = y_true - y_naive
    
    # Clean vs Naive
    d_clean_sq = (e_clean ** 2) - (e_naive ** 2)
    d_clean_abs = np.abs(e_clean) - np.abs(e_naive)
    dm_clean_sq = cluster_robust_dm(d_clean_sq, clusters)
    dm_clean_abs = cluster_robust_dm(d_clean_abs, clusters)
    
    # Deployed vs Naive
    d_dep_sq = (e_dep ** 2) - (e_naive ** 2)
    d_dep_abs = np.abs(e_dep) - np.abs(e_naive)
    dm_dep_sq = cluster_robust_dm(d_dep_sq, clusters)
    dm_dep_abs = cluster_robust_dm(d_dep_abs, clusters)
    
    # Clean vs Deployed
    d_clean_vs_dep_sq = (e_clean ** 2) - (e_dep ** 2)
    dm_clean_vs_dep = cluster_robust_dm(d_clean_vs_dep_sq, clusters)
    
    # State-level wins
    u_cl = np.unique(clusters)
    clean_wins_sq = sum(np.sum(d_clean_sq[clusters == c]) < 0 for c in u_cl)
    dep_wins_sq = sum(np.sum(d_dep_sq[clusters == c]) < 0 for c in u_cl)
    
    print("=" * 90)
    print(f"EVALUATION: {split_name} (N={len(y_true)} windows across {len(u_cl)} states)")
    print("=" * 90)
    print(f"{'Metric':<18} | {'Clean Retrained (expm1)':<23} | {'Original Deployed (expm1)':<25} | {'Naive Persistence (y_t-1)':<25}")
    print("-" * 90)
    print(f"{'WAPE (%)':<18} | {m_clean['wape']:<23.2f} | {m_deployed['wape']:<25.2f} | {m_naive['wape']:<25.2f}")
    print(f"{'MAPE (%)':<18} | {m_clean['mape']:<23.2f} | {m_deployed['mape']:<25.2f} | {m_naive['mape']:<25.2f}")
    print(f"{'MAE (cases)':<18} | {m_clean['mae']:<23,.1f} | {m_deployed['mae']:<25,.1f} | {m_naive['mae']:<25,.1f}")
    print(f"{'RMSE (cases)':<18} | {m_clean['rmse']:<23,.1f} | {m_deployed['rmse']:<25,.1f} | {m_naive['rmse']:<25,.1f}")
    print(f"{'R^2':<18} | {m_clean['r2']:<23.4f} | {m_deployed['r2']:<25.4f} | {m_naive['r2']:<25.4f}")
    print("-" * 90)
    print(f"Cluster-Robust DM (Squared Loss vs Naive):")
    print(f"  Clean Retrained:   t = {dm_clean_sq['t_stat']:+.4f}, p = {dm_clean_sq['p_value']:.4f} (df=29) | State wins: {clean_wins_sq}/{len(u_cl)} ({clean_wins_sq/len(u_cl)*100:.1f}%)")
    print(f"  Original Deployed: t = {dm_dep_sq['t_stat']:+.4f}, p = {dm_dep_sq['p_value']:.4f} (df=29) | State wins: {dep_wins_sq}/{len(u_cl)} ({dep_wins_sq/len(u_cl)*100:.1f}%)")
    print(f"Clean vs Deployed DM (Squared Loss): t = {dm_clean_vs_dep['t_stat']:+.4f}, p = {dm_clean_vs_dep['p_value']:.4f}")
    print("=" * 90 + "\n")
    
    return {
        "split_name": split_name,
        "n_windows": len(y_true),
        "clean_model": m_clean,
        "deployed_model": m_deployed,
        "naive_baseline": m_naive,
        "dm_clean_vs_naive_sq": dm_clean_sq,
        "dm_clean_vs_naive_abs": dm_clean_abs,
        "dm_deployed_vs_naive_sq": dm_dep_sq,
        "dm_deployed_vs_naive_abs": dm_dep_abs,
        "dm_clean_vs_deployed_sq": dm_clean_vs_dep,
        "state_wins": {
            "clean_sq": int(clean_wins_sq),
            "deployed_sq": int(dep_wins_sq),
            "total_states": int(len(u_cl)),
        }
    }


def main():
    print("Loading authentic surveillance and constructing feature matrix...")
    df_all, feature_cols, meta = build_dataset()
    
    # Chronological Split:
    # Train: 2020-06 to 2021-03 (10 months x 30 states = 300 windows)
    # Test Delta: 2021-04 to 2021-07 (4 months x 30 states = 120 windows)
    # Test Full Out-of-Sample: 2021-04 to 2021-10 (7 months x 30 states = 210 windows)
    df_train = df_all[df_all["date"] <= "2021-03-01"].copy()
    df_delta = df_all[(df_all["date"] >= "2021-04-01") & (df_all["date"] <= "2021-07-01")].copy()
    df_full_oos = df_all[df_all["date"] >= "2021-04-01"].copy()
    
    print(f"Training set: {len(df_train)} windows ({df_train['date'].min()} to {df_train['date'].max()})")
    print(f"Delta test set: {len(df_delta)} windows ({df_delta['date'].min()} to {df_delta['date'].max()})")
    print(f"Full OOS test set: {len(df_full_oos)} windows ({df_full_oos['date'].min()} to {df_full_oos['date'].max()})")
    
    print("\nTraining clean XGBoost model on authentic pre-Delta data...")
    clean_model = train_clean_model(df_train, feature_cols)
    with open(OUTPUT_MODEL_PATH, "wb") as f:
        pickle.dump(clean_model, f)
    print(f"Saved clean authentic model to: {OUTPUT_MODEL_PATH}")
    
    print("\nLoading original deployed ForecastPredictor artifact...")
    deployed_pred = ForecastPredictor()
    deployed_pred.load_model()
    
    res_delta = evaluate_split(df_delta, clean_model, deployed_pred, feature_cols, "Delta Wave Surge (Apr - Jul 2021)")
    res_full_oos = evaluate_split(df_full_oos, clean_model, deployed_pred, feature_cols, "Full Out-of-Sample Surge & Decline (Apr - Oct 2021)")
    
    all_results = {
        "metadata": {
            "dataset": "authentic_covid_surveillance.csv",
            "clean_model_trained_on": "Pre-Delta Wave 1 (2020-06-01 to 2021-03-01, N=300)",
            "deployed_artifact_origin": "Trained on synthetic-augmented 10x-inflated data (legacy)",
            "evaluation_date": "2026-09-20",
        },
        "delta_evaluation": res_delta,
        "full_oos_evaluation": res_full_oos,
    }
    
    with open(RESULTS_JSON, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"Complete comparative results saved to: {RESULTS_JSON}")


if __name__ == "__main__":
    main()
