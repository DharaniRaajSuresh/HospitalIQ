"""
ml_pipeline/multiwave_surveillance_eval.py
Step 5: Multi-Wave Authentic Surveillance Benchmark (Delta vs. Omicron)
Evaluates the deployed forecast model artifact (forecast_cases_model.pkl) strictly
on out-of-sample surveillance waves:
  - Wave 2 (Delta Peak): April 1, 2021 to July 31, 2021 (N = 120 windows, 30 states)
  - Wave 3 (Omicron Wave): December 1, 2021 to March 31, 2022 (N = 114 windows, 29 states)
  * Note: Wave 1 (June 2020 to February 2021) is strictly excluded to prevent
    training-set evaluation leakage.

Statistical tests per wave and pooled:
  - Diebold-Mariano test with state-clustered robust standard errors (absolute loss)
  - Diebold-Mariano test with state-clustered robust standard errors (squared loss)
  - Paired Wilcoxon signed-rank test
  - TOST equivalence test at 5% and 2% margins
  - Family-Wise Error Rate (FWER) control via Holm-Bonferroni correction (M = 15 tests)

Outputs:
    paper_revision/results/multiwave_surveillance_results.json
"""

import json, os, pickle, math
import numpy as np
import pandas as pd
from scipy import stats

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")
RAW_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "raw")
RESULTS_DIR = os.path.join(HOSPI, "paper_revision", "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# ── Load model & metadata ──────────────────────────────────────────────────────
model = pickle.load(open(os.path.join(MODELS_DIR, "forecast_cases_model.pkl"), "rb"))
meta  = pickle.load(open(os.path.join(MODELS_DIR, "forecast_metadata.pkl"), "rb"))

FEATURE_COLS     = meta["feature_cols"]
DISEASE_ENCODING = meta["disease_encoding"]
STATE_ENCODING   = meta.get("state_encoding", {})
STATE_BEDS       = meta.get("state_beds", {})
DISEASE_PARAMS   = meta.get("disease_params", {})
covid_params     = DISEASE_PARAMS.get("COVID-19", {"cfr": 0.5808505681238239, "r0": 0.9560405420944372})

# ── Load authentic outbreak data ───────────────────────────────────────────────
df = pd.read_csv(os.path.join(RAW_DIR, "outbreak_real.csv"), parse_dates=["date"])
covid = df[(df["source"] == "COVID19-India API") & (df["state"].notna())].copy()
covid = covid.sort_values(["state", "date"]).reset_index(drop=True)

def build_wave_dataset(start_date, end_date):
    wave_mask = (covid["date"] >= start_date) & (covid["date"] <= end_date)
    wave_df = covid[wave_mask].copy()
    records = []
    
    for _, row in wave_df.iterrows():
        state = row["state"]
        date = row["date"]
        y_true = float(row["confirmed_cases"])
        
        hist = covid[(covid["state"] == state) & (covid["date"] < date)].sort_values("date")
        if len(hist) < 3:
            continue
            
        lag1 = float(hist.iloc[-1]["confirmed_cases"])
        lag2 = float(hist.iloc[-2]["confirmed_cases"])
        lag3 = float(hist.iloc[-3]["confirmed_cases"])
        lag1d = float(hist.iloc[-1]["deaths"])
        lag2d = float(hist.iloc[-2]["deaths"])
        ma3 = float(hist.tail(3)["confirmed_cases"].mean())
        growth = (lag1 - lag2) / max(lag2, 1)
        
        month = date.month
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)
        year_norm = (date.year - 2017) / 15
        
        beds_info = STATE_BEDS.get(state, {})
        state_beds_val = float(beds_info.get("total_beds", 1000))
        state_hosp_val = float(beds_info.get("hospitals", 10))
        disease_enc = float(DISEASE_ENCODING.get("COVID-19", 0))
        state_enc = float(STATE_ENCODING.get(state, 0))
        
        feat = {
            "month_sin": month_sin,
            "month_cos": month_cos,
            "year_normalized": year_norm,
            "lag_1_cases": lag1,
            "lag_2_cases": lag2,
            "lag_3_cases": lag3,
            "lag_1_deaths": lag1d,
            "lag_2_deaths": lag2d,
            "cases_ma3": ma3,
            "cases_growth": growth,
            "disease_cfr": covid_params["cfr"],
            "disease_r0": covid_params["r0"],
            "state_beds": state_beds_val,
            "state_hospitals": state_hosp_val,
            "disease_enc": disease_enc,
            "state_enc": state_enc,
        }
        
        x_vec = np.array([feat[c] for c in FEATURE_COLS]).reshape(1, -1)
        y_pred = float(max(0, model.predict(x_vec)[0]))
        y_persist = lag1
        
        records.append({
            "state": state,
            "date": str(date)[:10],
            "y_true": y_true,
            "y_pred": y_pred,
            "y_persist": y_persist,
            "abs_err_model": abs(y_true - y_pred),
            "abs_err_persist": abs(y_true - y_persist),
            "sq_err_model": (y_true - y_pred)**2,
            "sq_err_persist": (y_true - y_persist)**2,
            "diff_abs": abs(y_true - y_pred) - abs(y_true - y_persist),
            "diff_sq": (y_true - y_pred)**2 - (y_true - y_persist)**2
        })
        
    return pd.DataFrame(records)

# Extract out-of-sample waves
delta_df = build_wave_dataset("2021-04-01", "2021-07-31")
omicron_df = build_wave_dataset("2021-12-01", "2022-03-31")
pooled_df = pd.concat([delta_df, omicron_df], ignore_index=True)

print(f"Delta Wave windows   : {len(delta_df)} across {delta_df['state'].nunique()} states")
print(f"Omicron Wave windows : {len(omicron_df)} across {omicron_df['state'].nunique()} states")
print(f"Pooled Total windows : {len(pooled_df)}")

# ── Statistical Testing Functions ──────────────────────────────────────────────
def cluster_robust_dm(df, loss_col="diff_abs"):
    """Paired Diebold-Mariano test with state-clustered variance."""
    states = df["state"].unique()
    K = len(states)
    d = df[loss_col].values
    d_bar = np.mean(d)
    
    # State cluster score sums
    s_k = np.array([df[df["state"] == s][loss_col].sum() for s in states])
    s_mean = np.mean(s_k)
    v_cluster = (K / (K - 1)) * np.sum((s_k - s_mean)**2)
    se_cluster = np.sqrt(v_cluster) / len(df)
    
    if se_cluster < 1e-12:
        return 0.0, 1.0
    t_stat = d_bar / se_cluster
    p_val = 2 * (1 - stats.t.cdf(abs(t_stat), df=K - 1))
    return float(t_stat), float(p_val)

def run_wave_stats(df, wave_name):
    y_t = df["y_true"].values
    y_m = df["y_pred"].values
    y_p = df["y_persist"].values
    
    wape_m = float(np.sum(np.abs(y_t - y_m)) / max(np.sum(y_t), 1) * 100)
    wape_p = float(np.sum(np.abs(y_t - y_p)) / max(np.sum(y_t), 1) * 100)
    
    # DM tests
    dm_abs_stat, dm_abs_p = cluster_robust_dm(df, "diff_abs")
    dm_sq_stat, dm_sq_p = cluster_robust_dm(df, "diff_sq")
    
    # Paired Wilcoxon signed-rank test
    w_res = stats.wilcoxon(df["abs_err_model"], df["abs_err_persist"], alternative="two-sided")
    wilcox_stat = float(w_res.statistic)
    wilcox_p = float(w_res.pvalue)
    
    # TOST Equivalence testing (against 5% and 2% margin of mean persistence error)
    mean_pe = np.mean(df["abs_err_persist"])
    diffs = df["diff_abs"].values
    mean_diff = np.mean(diffs)
    se_diff = np.std(diffs, ddof=1) / np.sqrt(len(diffs))
    
    # Margin 5%
    delta_5 = 0.05 * mean_pe
    t1_5 = (mean_diff - (-delta_5)) / se_diff
    t2_5 = (delta_5 - mean_diff) / se_diff
    p1_5 = 1 - stats.t.cdf(t1_5, df=len(diffs)-1)
    p2_5 = 1 - stats.t.cdf(t2_5, df=len(diffs)-1)
    tost_5_p = float(max(p1_5, p2_5))
    
    # Margin 2%
    delta_2 = 0.02 * mean_pe
    t1_2 = (mean_diff - (-delta_2)) / se_diff
    t2_2 = (delta_2 - mean_diff) / se_diff
    p1_2 = 1 - stats.t.cdf(t1_2, df=len(diffs)-1)
    p2_2 = 1 - stats.t.cdf(t2_2, df=len(diffs)-1)
    tost_2_p = float(max(p1_2, p2_2))
    
    return {
        "wave": wave_name,
        "n_windows": len(df),
        "n_states": int(df["state"].nunique()),
        "wape_deployed_model": round(wape_m, 2),
        "wape_naive_persistence": round(wape_p, 2),
        "tests": {
            "dm_cluster_abs": {"stat": dm_abs_stat, "p_raw": dm_abs_p},
            "dm_cluster_sq":  {"stat": dm_sq_stat,  "p_raw": dm_sq_p},
            "wilcoxon_signed": {"stat": wilcox_stat, "p_raw": wilcox_p},
            "tost_margin_5pct": {"stat": float(min(t1_5, t2_5)), "p_raw": tost_5_p},
            "tost_margin_2pct": {"stat": float(min(t1_2, t2_2)), "p_raw": tost_2_p}
        }
    }

delta_results  = run_wave_stats(delta_df, "Wave 2 (Delta)")
omicron_results = run_wave_stats(omicron_df, "Wave 3 (Omicron)")
pooled_results  = run_wave_stats(pooled_df, "Pooled Out-of-Sample (Delta + Omicron)")

# ── Holm-Bonferroni Correction Across All 15 Hypotheses ────────────────────────
test_family = []
for res in [delta_results, omicron_results, pooled_results]:
    w_name = res["wave"]
    for t_key, t_data in res["tests"].items():
        test_family.append({
            "wave": w_name,
            "test": t_key,
            "stat": t_data["stat"],
            "p_raw": t_data["p_raw"]
        })

# Sort by p_raw ascending
test_family.sort(key=lambda x: x["p_raw"])
M = len(test_family) # 15 tests

cum_max = 0.0
for rank, item in enumerate(test_family):
    p_r = item["p_raw"]
    mult = M - rank
    p_adj = min(1.0, mult * p_r)
    cum_max = max(cum_max, p_adj)
    item["rank"] = rank + 1
    item["multiplier"] = mult
    item["p_holm"] = round(float(cum_max), 6)
    item["reject_null_05"] = bool(item["p_holm"] < 0.05)

# Attach adjusted p-values back to wave results
for item in test_family:
    w = item["wave"]
    t = item["test"]
    target_res = pooled_results if "Pooled" in w else (delta_results if "Delta" in w else omicron_results)
    target_res["tests"][t]["p_holm"] = item["p_holm"]
    target_res["tests"][t]["significant_at_05"] = item["reject_null_05"]

print("\n" + "="*80)
print(f"MULTI-WAVE SURVEILLANCE & HOLM-BONFERRONI CORRECTION MATRIX (M={M} Tests)")
print("="*80)
print(f"{'Wave':20s} | {'Test':18s} | {'Stat':9s} | {'p (Raw)':10s} | {'p (Holm)':10s} | {'Sig (alpha=0.05)'}")
print("-" * 80)
for item in test_family:
    print(f"{item['wave']:20s} | {item['test']:18s} | {item['stat']:9.4f} | {item['p_raw']:10.6e} | {item['p_holm']:10.6f} | {item['reject_null_05']}")

print("\nSummary Findings:")
print(f"  Delta   : Model WAPE = {delta_results['wape_deployed_model']}%, Persistence WAPE = {delta_results['wape_naive_persistence']}%")
print(f"  Omicron : Model WAPE = {omicron_results['wape_deployed_model']}%, Persistence WAPE = {omicron_results['wape_naive_persistence']}%")
print(f"  Pooled  : Model WAPE = {pooled_results['wape_deployed_model']}%, Persistence WAPE = {pooled_results['wape_naive_persistence']}%")

final_payload = {
    "benchmark": "multiwave_out_of_sample_surveillance",
    "leakage_note": "Wave 1 (June 2020 - Feb 2021) strictly excluded as training data.",
    "waves": {
        "delta": delta_results,
        "omicron": omicron_results,
        "pooled": pooled_results
    },
    "holm_bonferroni_family": test_family
}

out_file = os.path.join(RESULTS_DIR, "multiwave_surveillance_results.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(final_payload, f, indent=2)

print(f"\n[SUCCESS] Multi-wave surveillance results saved to {out_file}")
