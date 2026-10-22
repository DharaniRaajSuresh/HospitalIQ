"""
grouped_permutation_importance.py  — Step 4
Grouped permutation importance for the forecast model on the 120 authentic Delta windows.
Pre-specified groups:
  - autoregressive_group: [lag_1_cases, lag_2_cases, lag_3_cases, cases_ma3]
  - all other features permuted individually

Seeds 200–229 (30 seeds), fixed before seeing results.
Output: paper_revision/results/grouped_permutation_results.json
"""
import json, os, math, pickle
import numpy as np
import pandas as pd
from scipy import stats

HOSPI      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")
RAW_DIR    = os.path.join(HOSPI, "ml_pipeline", "data", "raw")
OUT_DIR    = os.path.join(HOSPI, "paper_revision", "results")
os.makedirs(OUT_DIR, exist_ok=True)

# Load model + metadata
model = pickle.load(open(os.path.join(MODELS_DIR, "forecast_cases_model.pkl"), "rb"))
meta  = pickle.load(open(os.path.join(MODELS_DIR, "forecast_metadata.pkl"),    "rb"))
FEATURE_COLS   = meta["feature_cols"]
STATE_ENCODING = meta.get("state_encoding", {})
STATE_BEDS     = meta.get("state_beds", {})
DISEASE_PARAMS = meta.get("disease_params", {})
DISEASE_ENC    = meta.get("disease_encoding", {})

# Pre-specified groups
AR_GROUP = ["lag_1_cases", "lag_2_cases", "lag_3_cases", "cases_ma3"]
SEEDS    = list(range(200, 230))   # 30 seeds, fixed

# Build feature matrix for 120 Delta windows
df    = pd.read_csv(os.path.join(RAW_DIR, "outbreak_real.csv"), parse_dates=["date"])
covid = df[(df["source"] == "COVID19-India API") & (df["state"].notna())].copy()
covid = covid.sort_values(["state", "date"]).reset_index(drop=True)
delta_mask = (covid["date"] >= "2021-04-01") & (covid["date"] <= "2021-07-31")
delta = covid[delta_mask].copy()

covid_params = DISEASE_PARAMS.get("COVID-19", {"cfr": 0.5808505681238239, "r0": 0.9560405420944372})

rows, y_true_list = [], []
for _, row in delta.iterrows():
    state, date = row["state"], row["date"]
    hist = covid[(covid["state"] == state) & (covid["date"] < date)].sort_values("date")
    if len(hist) < 3:
        continue
    lag1, lag2, lag3 = (float(hist.iloc[-i]["confirmed_cases"]) for i in [1, 2, 3])
    lag1d, lag2d     = (float(hist.iloc[-i]["deaths"]) for i in [1, 2])
    ma3    = float(hist.tail(3)["confirmed_cases"].mean())
    growth = (lag1 - lag2) / max(lag2, 1)
    m      = date.month
    beds_info = STATE_BEDS.get(state, {})
    feat = {
        "month_sin":       math.sin(2 * math.pi * m / 12),
        "month_cos":       math.cos(2 * math.pi * m / 12),
        "year_normalized": (date.year - 2017) / 15,
        "lag_1_cases": lag1, "lag_2_cases": lag2, "lag_3_cases": lag3,
        "lag_1_deaths": lag1d, "lag_2_deaths": lag2d,
        "cases_ma3": ma3, "cases_growth": growth,
        "disease_cfr":     covid_params["cfr"],
        "disease_r0":      covid_params["r0"],
        "state_beds":      float(beds_info.get("total_beds", 1000)),
        "state_hospitals": float(beds_info.get("hospitals", 10)),
        "disease_enc":     float(DISEASE_ENC.get("COVID-19", 0)),
        "state_enc":       float(STATE_ENCODING.get(state, 0)),
    }
    rows.append([feat[c] for c in FEATURE_COLS])
    y_true_list.append(float(row["confirmed_cases"]))

X      = np.array(rows)
y_true = np.array(y_true_list)
n      = len(y_true)
print(f"Evaluation set: {n} rows")

def wape(y, yhat):
    return np.sum(np.abs(y - yhat)) / np.sum(np.abs(y)) * 100

baseline_wape = wape(y_true, model.predict(X))
print(f"Baseline WAPE: {baseline_wape:.4f}%")

def permutation_importance_single(feat_idx, n_reps=30, seeds=SEEDS):
    """Permute a single feature index."""
    deltas = []
    for seed in seeds[:n_reps]:
        rng    = np.random.RandomState(seed)
        X_perm = X.copy()
        X_perm[:, feat_idx] = rng.permutation(X[:, feat_idx])
        deltas.append(wape(y_true, model.predict(X_perm)) - baseline_wape)
    return np.mean(deltas), np.std(deltas), deltas

def permutation_importance_group(feat_indices, n_reps=30, seeds=SEEDS):
    """Permute a group of features simultaneously."""
    deltas = []
    for seed in seeds[:n_reps]:
        rng    = np.random.RandomState(seed)
        X_perm = X.copy()
        perm   = rng.permutation(n)
        for idx in feat_indices:
            X_perm[:, idx] = X_perm[:, idx][perm]
        deltas.append(wape(y_true, model.predict(X_perm)) - baseline_wape)
    return np.mean(deltas), np.std(deltas), deltas

results = {"baseline_wape": baseline_wape, "n_windows": n, "seeds": SEEDS}

# Individual feature importances
print("\nIndividual feature importances:")
individual = {}
for fi, fname in enumerate(FEATURE_COLS):
    mean_d, std_d, deltas = permutation_importance_single(fi)
    ci_lo = np.percentile(deltas, 2.5)
    ci_hi = np.percentile(deltas, 97.5)
    individual[fname] = {"mean_delta_wape": mean_d, "std": std_d, "ci_95_lo": ci_lo, "ci_95_hi": ci_hi}
    print(f"  {fname:20s}: +{mean_d:.2f}% WAPE  [{ci_lo:.2f}, {ci_hi:.2f}]")
results["individual"] = individual

# Grouped AR importance
ar_indices = [FEATURE_COLS.index(f) for f in AR_GROUP]
print(f"\nGrouped AR permutation ({AR_GROUP}):")
mean_gr, std_gr, deltas_gr = permutation_importance_group(ar_indices)
ci_lo_gr = np.percentile(deltas_gr, 2.5)
ci_hi_gr = np.percentile(deltas_gr, 97.5)
print(f"  Group delta WAPE: +{mean_gr:.2f}%  [{ci_lo_gr:.2f}, {ci_hi_gr:.2f}]")

# Sum of individual AR gains
sum_individual_ar = sum(individual[f]["mean_delta_wape"] for f in AR_GROUP)
total_gain        = sum(v["mean_delta_wape"] for v in individual.values() if v["mean_delta_wape"] > 0)
group_share       = mean_gr / total_gain * 100 if total_gain > 0 else float('nan')
lag1_share        = individual["lag_1_cases"]["mean_delta_wape"] / total_gain * 100 if total_gain > 0 else float('nan')

print(f"\n  Sum of individual AR gains: {sum_individual_ar:.2f}%")
print(f"  Group gain share of total: {group_share:.1f}%")
print(f"  lag_1 single-feature share: {lag1_share:.1f}%")
print(f"\n  NOTE: If group gain < sum of individual gains, features are redundant within group.")
print(f"  NOTE: If group gain > lag_1 alone, the '55% lag_1 dominance' claim should be")
print(f"        reframed as 'AR group dominance' — the whole block together, not just lag_1.")

results["ar_group"] = {
    "features":          AR_GROUP,
    "mean_delta_wape":   mean_gr,
    "std":               std_gr,
    "ci_95_lo":          ci_lo_gr,
    "ci_95_hi":          ci_hi_gr,
    "sum_individual_ar": sum_individual_ar,
    "group_share_pct":   group_share,
    "lag1_single_share": lag1_share,
}

out_path = os.path.join(OUT_DIR, "grouped_permutation_results.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {out_path}")
