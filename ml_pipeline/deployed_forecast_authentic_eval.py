"""
deployed_forecast_authentic_eval.py
Step 3: Run the deployed forecast artifact (forecast_cases_model.pkl) on the
120 authentic Delta-wave surveillance windows (Apr–Jul 2021, 30 Indian states)
and perform a paired Diebold–Mariano test with state-clustered errors.

Pre-specified (committed before looking at output):
  - Primary loss:   absolute loss |y - yhat|
  - Secondary loss: squared loss (y - yhat)^2
  - Cluster unit:   state
  - Alternative:    two-sided
  - Output file:    paper_revision/results/deployed_forecast_authentic.json

DO NOT modify this script after running it. Any changes must be in a new script
with a documented reason.
"""

import json, os, pickle
import numpy as np
import pandas as pd
from scipy import stats

# ── paths ──────────────────────────────────────────────────────────────────────
HOSPI      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")
RAW_DIR    = os.path.join(HOSPI, "ml_pipeline", "data", "raw")
OUT_DIR    = os.path.join(HOSPI, "paper_revision", "results")
os.makedirs(OUT_DIR, exist_ok=True)

# ── load model + metadata ──────────────────────────────────────────────────────
model = pickle.load(open(os.path.join(MODELS_DIR, "forecast_cases_model.pkl"), "rb"))
meta  = pickle.load(open(os.path.join(MODELS_DIR, "forecast_metadata.pkl"),    "rb"))

FEATURE_COLS     = meta["feature_cols"]
DISEASE_ENCODING = meta["disease_encoding"]
STATE_ENCODING   = meta.get("state_encoding", {})
STATE_BEDS       = meta.get("state_beds", {})
DISEASE_PARAMS   = meta.get("disease_params", {})

print(f"Model n_features_in_: {model.n_features_in_}")
print(f"Feature cols ({len(FEATURE_COLS)}): {FEATURE_COLS}")

# Scaler: XGBoost doesn't need scaling; skip corrupt scaler
scaler = None

# ── load authentic data ────────────────────────────────────────────────────────
df    = pd.read_csv(os.path.join(RAW_DIR, "outbreak_real.csv"), parse_dates=["date"])
covid = df[(df["source"] == "COVID19-India API") & (df["state"].notna())].copy()
covid = covid.sort_values(["state", "date"]).reset_index(drop=True)

# Delta window: April–July 2021 (pre-specified)
delta_mask = (covid["date"] >= "2021-04-01") & (covid["date"] <= "2021-07-31")
delta      = covid[delta_mask].copy()
print(f"\nDelta window: {len(delta)} rows, {delta['state'].nunique()} states")
print(f"Months: {sorted(delta['date'].dt.to_period('M').unique().astype(str).tolist())}")

# ── build lag features for each Delta row ──────────────────────────────────────
import math

# Default COVID params from metadata (use stored values from training)
covid_params = DISEASE_PARAMS.get("COVID-19", {"cfr": 0.5808505681238239, "r0": 0.9560405420944372})

records = []
for _, row in delta.iterrows():
    state  = row["state"]
    date   = row["date"]
    y_true = float(row["confirmed_cases"])

    # Historical records for this state before this date
    hist = covid[(covid["state"] == state) & (covid["date"] < date)].sort_values("date")
    if len(hist) < 3:
        print(f"  SKIP {state} {date}: insufficient history ({len(hist)} rows)")
        continue

    lag1   = float(hist.iloc[-1]["confirmed_cases"])
    lag2   = float(hist.iloc[-2]["confirmed_cases"])
    lag3   = float(hist.iloc[-3]["confirmed_cases"])
    lag1d  = float(hist.iloc[-1]["deaths"])
    lag2d  = float(hist.iloc[-2]["deaths"])
    ma3    = float(hist.tail(3)["confirmed_cases"].mean())
    growth = (lag1 - lag2) / max(lag2, 1)

    month     = date.month
    month_sin = math.sin(2 * math.pi * month / 12)
    month_cos = math.cos(2 * math.pi * month / 12)
    year_norm = (date.year - 2017) / 15

    beds_info       = STATE_BEDS.get(state, {})
    state_beds_val  = float(beds_info.get("total_beds",  1000))
    state_hosp_val  = float(beds_info.get("hospitals",   10))
    disease_enc     = float(DISEASE_ENCODING.get("COVID-19", 0))
    state_enc       = float(STATE_ENCODING.get(state, 0))

    feat = {
        "month_sin":       month_sin,
        "month_cos":       month_cos,
        "year_normalized": year_norm,
        "lag_1_cases":     lag1,
        "lag_2_cases":     lag2,
        "lag_3_cases":     lag3,
        "lag_1_deaths":    lag1d,
        "lag_2_deaths":    lag2d,
        "cases_ma3":       ma3,
        "cases_growth":    growth,
        "disease_cfr":     covid_params["cfr"],
        "disease_r0":      covid_params["r0"],
        "state_beds":      state_beds_val,
        "state_hospitals": state_hosp_val,
        "disease_enc":     disease_enc,
        "state_enc":       state_enc,
    }

    X      = np.array([[feat[c] for c in FEATURE_COLS]])
    y_pred = float(model.predict(X)[0])
    y_pers = lag1  # naive persistence

    records.append({
        "state":         state,
        "date":          str(date.date()),
        "y_true":        y_true,
        "y_pred":        y_pred,
        "y_persistence": y_pers,
    })

df_res = pd.DataFrame(records)
print(f"\nValid evaluation rows: {len(df_res)}")

# ── compute losses ─────────────────────────────────────────────────────────────
df_res["loss_abs_model"]       = np.abs(df_res["y_true"] - df_res["y_pred"])
df_res["loss_abs_persistence"] = np.abs(df_res["y_true"] - df_res["y_persistence"])
df_res["loss_sq_model"]        = (df_res["y_true"] - df_res["y_pred"])**2
df_res["loss_sq_persistence"]  = (df_res["y_true"] - df_res["y_persistence"])**2

df_res["d_abs"] = df_res["loss_abs_model"] - df_res["loss_abs_persistence"]
df_res["d_sq"]  = df_res["loss_sq_model"]  - df_res["loss_sq_persistence"]

# ── cluster-robust DM test (state clusters) ────────────────────────────────────
def cluster_robust_dm(d, clusters):
    """
    Paired Diebold-Mariano with cluster-robust SE.
    d[i] = loss_model[i] - loss_baseline[i]
    Positive d_bar means model is WORSE than baseline.
    """
    n      = len(d)
    d_bar  = np.mean(d)
    unique = np.unique(clusters)
    G      = len(unique)
    cluster_sums = np.array([d[clusters == c].sum() for c in unique])
    V_cr   = np.sum(cluster_sums**2) / (n**2)
    SE_cr  = np.sqrt(V_cr)
    dm     = d_bar / SE_cr
    p_val  = 2 * stats.t.sf(np.abs(dm), df=G - 1)
    return float(dm), float(p_val), float(d_bar), float(SE_cr), G

d_abs    = df_res["d_abs"].values
d_sq     = df_res["d_sq"].values
clusters = df_res["state"].values

dm_abs, p_abs, d_bar_abs, se_abs, n_cl = cluster_robust_dm(d_abs, clusters)
dm_sq,  p_sq,  d_bar_sq,  se_sq,  _   = cluster_robust_dm(d_sq,  clusters)

print(f"\n=== Diebold–Mariano (cluster-robust, {n_cl} state clusters) ===")
print(f"PRIMARY  — Absolute loss:  DM={dm_abs:.4f}, p={p_abs:.4f}, mean_d={d_bar_abs:.1f}")
print(f"SECONDARY — Squared loss:  DM={dm_sq:.4f},  p={p_sq:.4f},  mean_d={d_bar_sq:.1f}")

# ── WAPE ───────────────────────────────────────────────────────────────────────
def wape(y_true, y_pred):
    return np.sum(np.abs(y_true - y_pred)) / np.sum(np.abs(y_true)) * 100

wape_model = wape(df_res["y_true"].values, df_res["y_pred"].values)
wape_pers  = wape(df_res["y_true"].values, df_res["y_persistence"].values)
print(f"\nWAPE deployed model: {wape_model:.2f}%")
print(f"WAPE persistence:    {wape_pers:.2f}%")

# ── Note on sign difference ────────────────────────────────────────────────────
if dm_abs > 0:
    sign_note = (
        "dm_abs > 0: deployed model has HIGHER absolute error than persistence "
        "(i.e., negative skill). Under squared loss the sign/significance may differ "
        "because squared loss amplifies large-error outliers differently. "
        "Primary conclusion (absolute loss): the deployed artifact does not improve "
        "over naive persistence on Delta-wave data."
    )
else:
    sign_note = (
        "dm_abs < 0: deployed model has LOWER absolute error than persistence "
        "(positive skill under absolute loss). Sign in squared loss may differ due to "
        "outlier sensitivity of squared loss."
    )
print(f"\nSign note: {sign_note}")

# Note on discrepancy with authoritative_results.json
discrepancy_note = (
    "The authoritative_results.json Wilcoxon p=0.1459 (pooled) and p=0.6731 (clustered) "
    "come from generate_final_paper_results.py, which re-trains a clean XGBoost on "
    "Wave-1 data (up to Apr 2021) with a differenced target, then evaluates on the same "
    "120 windows. THIS script evaluates the deployed artifact (forecast_cases_model.pkl), "
    "which was trained on the full synthetic-augmented dataset and uses different features "
    "(including disease_cfr, disease_r0, state_beds from the DB). The two evaluations "
    "measure different things: (1) can a clean re-trained model beat persistence? and "
    "(2) does the deployed production artifact beat persistence? Results may legitimately "
    "differ. The paper must distinguish these two evaluations clearly."
)
print(f"\nDiscrepancy note: {discrepancy_note[:200]}...")

# ── save ───────────────────────────────────────────────────────────────────────
results = {
    "script":            "deployed_forecast_authentic_eval.py",
    "model_artifact":    "forecast_cases_model.pkl",
    "n_windows":         len(df_res),
    "n_states":          int(df_res["state"].nunique()),
    "date_range":        ["2021-04-01", "2021-07-31"],
    "primary_loss":      "absolute",
    "dm_absolute": {
        "statistic": dm_abs,
        "p_value":   p_abs,
        "mean_d":    d_bar_abs,
        "se_cr":     se_abs,
        "df":        n_cl - 1,
    },
    "dm_squared": {
        "statistic": dm_sq,
        "p_value":   p_sq,
        "mean_d":    d_bar_sq,
        "se_cr":     se_sq,
        "df":        n_cl - 1,
    },
    "wape_model":        wape_model,
    "wape_persistence":  wape_pers,
    "sign_note":         sign_note,
    "discrepancy_note":  discrepancy_note,
}

out_path = os.path.join(OUT_DIR, "deployed_forecast_authentic.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {out_path}")
