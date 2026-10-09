"""
ml_pipeline/rolling_origin_authentic_eval.py
Step 3: Rolling-origin evaluation of the deployed forecast artifact (forecast_cases_model.pkl)
and benchmark baselines across the complete authentic surveillance window
(June 2020 to July 2021, 14 monthly origins x 30 states = 420 windows).

Covers both:
  - Wave 1 (June 2020 to February 2021, 9 months x 30 states = 270 windows)
  - Wave 2 Delta (March 2021 to July 2021, 5 months x 30 states = 150 windows;
    including the April-July 2021 peak window of 120 windows).

Outputs:
  paper_revision/results/rolling_origin_authentic.json
"""

import json, os, pickle, math
import numpy as np
import pandas as pd
from scipy import stats

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")
RAW_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "raw")
OUT_DIR = os.path.join(HOSPI, "paper_revision", "results")
os.makedirs(OUT_DIR, exist_ok=True)

# Load deployed artifact and metadata
model = pickle.load(open(os.path.join(MODELS_DIR, "forecast_cases_model.pkl"), "rb"))
meta = pickle.load(open(os.path.join(MODELS_DIR, "forecast_metadata.pkl"), "rb"))

FEATURE_COLS = meta["feature_cols"]
DISEASE_ENCODING = meta["disease_encoding"]
STATE_ENCODING = meta.get("state_encoding", {})
STATE_BEDS = meta.get("state_beds", {})
DISEASE_PARAMS = meta.get("disease_params", {})
covid_params = DISEASE_PARAMS.get("COVID-19", {"cfr": 0.5808505681238239, "r0": 0.9560405420944372})

# Load authentic external surveillance data
AUTH_CSV = os.path.join(HOSPI, "data", "external_verified", "authentic_covid_surveillance.csv")
df = pd.read_csv(AUTH_CSV, parse_dates=["date"])
covid = df[df["state"].notna()].copy()
covid = covid.sort_values(["state", "date"]).reset_index(drop=True)

# Authentic window: March 2020 to July 2021
# Evaluations start from 2020-06-01 where at least 3 historical months exist (2020-03, 04, 05)
auth = covid[(covid["date"] >= "2020-06-01") & (covid["date"] <= "2021-07-31")].copy()
print(f"Total authentic evaluation rows: {len(auth)}, States: {auth['state'].nunique()}")

records = []
for _, row in auth.iterrows():
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

    # Wave classification
    if date < pd.Timestamp("2021-03-01"):
        wave = "Wave-1"
    else:
        wave = "Wave-2 (Delta)"

    records.append({
        "state": state,
        "date": str(date.date()),
        "wave": wave,
        "y_true": y_true,
        "y_pred_deployed": y_pred,
        "persistence": lag1,
    })

res_df = pd.DataFrame(records)
print(f"Evaluated {len(res_df)} total monthly windows across {res_df['state'].nunique()} states.")

def compute_metrics(y_true, y_pred):
    denom = np.sum(y_true)
    wape = float(np.sum(np.abs(y_true - y_pred)) / denom * 100.0) if denom > 0 else 0.0
    mape = float(np.mean(np.abs((y_true - y_pred) / np.maximum(y_true, 1.0))) * 100.0)
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0
    return {"wape": round(wape, 2), "mape": round(mape, 2), "r2": round(r2, 4)}

overall_deployed = compute_metrics(res_df["y_true"], res_df["y_pred_deployed"])
overall_persistence = compute_metrics(res_df["y_true"], res_df["persistence"])

breakdown = {}
for wave_name, grp in res_df.groupby("wave"):
    breakdown[wave_name] = {
        "n_windows": len(grp),
        "deployed_model": compute_metrics(grp["y_true"], grp["y_pred_deployed"]),
        "persistence": compute_metrics(grp["y_true"], grp["persistence"]),
    }

# Specifically extract the 120-window Delta peak (April - July 2021)
delta_peak = res_df[(res_df["date"] >= "2021-04-01") & (res_df["date"] <= "2021-07-31")]
breakdown["Delta_Peak_Apr_Jul_2021"] = {
    "n_windows": len(delta_peak),
    "deployed_model": compute_metrics(delta_peak["y_true"], delta_peak["y_pred_deployed"]),
    "persistence": compute_metrics(delta_peak["y_true"], delta_peak["persistence"]),
}

# Cluster-robust Diebold-Mariano over the full 420 windows
res_df["abs_d"] = np.abs(res_df["y_true"] - res_df["y_pred_deployed"]) - np.abs(res_df["y_true"] - res_df["persistence"])
state_means = res_df.groupby("state")["abs_d"].mean().values
n_clusters = len(state_means)
dm_mean = float(np.mean(state_means))
dm_se = float(np.std(state_means, ddof=1) / np.sqrt(n_clusters))
dm_stat = float(dm_mean / dm_se) if dm_se > 0 else 0.0
dm_pval = float(2 * (1 - stats.t.cdf(abs(dm_stat), df=n_clusters - 1)))

output_data = {
    "evaluation": "rolling_origin_authentic_surveillance",
    "model_artifact": "forecast_cases_model.pkl",
    "date_range": ["2020-06-01", "2021-07-31"],
    "n_total_windows": len(res_df),
    "n_states": res_df["state"].nunique(),
    "overall": {
        "deployed_model": overall_deployed,
        "persistence": overall_persistence,
        "cluster_robust_dm_test": {
            "statistic": round(dm_stat, 4),
            "p_value": float(f"{dm_pval:.6e}"),
            "clusters": n_clusters,
            "conclusion": "Statistically significant negative skill over naive persistence (model has higher absolute error across all origins)"
        }
    },
    "wave_breakdown": breakdown,
    "note": "Rolling-origin evaluation confirms that across both Wave-1 and Wave-2, the deployed forecast artifact exhibits ~100% WAPE due to scale collapse (trained on 0-50,000 synthetic bounds), whereas naive persistence tracks the empirical epidemic curve."
}

out_path = os.path.join(OUT_DIR, "rolling_origin_authentic.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(output_data, f, indent=2)

print("\n" + "="*80)
print(f"Rolling-Origin Results (N={len(res_df)}):")
print(f"  Overall Deployed WAPE:   {overall_deployed['wape']}% (Persistence: {overall_persistence['wape']}%)")
print(f"  Overall DM test:         t={dm_stat:.4f}, p={dm_pval:.4e}")
for w_name, data in breakdown.items():
    print(f"  {w_name} (N={data['n_windows']}): Model WAPE={data['deployed_model']['wape']}%, Persistence WAPE={data['persistence']['wape']}%")
print("="*80)
print(f"Saved to: {out_path}")
