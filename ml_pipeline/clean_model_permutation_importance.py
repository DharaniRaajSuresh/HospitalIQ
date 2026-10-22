"""
clean_model_permutation_importance.py
Permutation importance on the clean re-trained XGBoost (the model whose
55% lag_1 gain share is cited in the paper). This is the model from
generate_final_paper_results.py, NOT the deployed forecast_cases_model.pkl.

The deployed model has WAPE=100% on Delta data (trained on synthetic scale,
out-of-distribution at inference on authentic cumulative case counts).
This clean model is retrained on Wave-1 authentic data only.
"""
import math, json, os
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

HOSPI   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "raw")
OUT_DIR = os.path.join(HOSPI, "paper_revision", "results")
os.makedirs(OUT_DIR, exist_ok=True)

df  = pd.read_csv(os.path.join(RAW_DIR, "outbreak_real.csv"))
cov = df[df["disease"] == "COVID-19"].copy()
cov["date"] = pd.to_datetime(cov["date"])
cov = cov.sort_values(["state", "date"]).reset_index(drop=True)
real_cov = cov[cov["date"] <= "2021-07-31"].copy()

def build_dataset(data_source):
    records = []
    for state, group in data_source.groupby("state"):
        g = group.sort_values("date").reset_index(drop=True)
        if len(g) < 4:
            continue
        for i in range(3, len(g)):
            row  = g.iloc[i]
            lag1 = g.iloc[i-1]
            lag2 = g.iloc[i-2]
            lag3 = g.iloc[i-3]
            m    = row["date"].month
            records.append({
                "date":         str(row["date"].date()),
                "state":        state,
                "month_sin":    math.sin(2 * math.pi * m / 12),
                "month_cos":    math.cos(2 * math.pi * m / 12),
                "lag_1_cases":  float(lag1["confirmed_cases"]),
                "lag_2_cases":  float(lag2["confirmed_cases"]),
                "lag_3_cases":  float(lag3["confirmed_cases"]),
                "cases_ma3":    float((lag1["confirmed_cases"] + lag2["confirmed_cases"] + lag3["confirmed_cases"]) / 3.0),
                "lag_1_diff":   float(lag1["confirmed_cases"] - lag2["confirmed_cases"]),
                "lag_2_diff":   float(lag2["confirmed_cases"] - lag3["confirmed_cases"]),
                "target_cases": float(row["confirmed_cases"]),
                "target_diff":  float(row["confirmed_cases"] - lag1["confirmed_cases"]),
            })
    return pd.DataFrame(records)

real_features = build_dataset(real_cov)
train_real    = real_features[real_features["date"] < "2021-04-01"].copy()
test_real     = real_features[real_features["date"] >= "2021-04-01"].copy()

DIFF_FEATURES = ["month_sin", "month_cos", "lag_1_diff", "lag_2_diff", "lag_1_cases", "cases_ma3"]

xgb_clean = XGBRegressor(
    n_estimators=200, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
    random_state=42, n_jobs=-1, verbosity=0
)
xgb_clean.fit(train_real[DIFF_FEATURES], train_real["target_diff"])

y_test   = test_real["target_cases"].values
lag1_arr = test_real["lag_1_cases"].values
X_test   = test_real[DIFF_FEATURES].values

def wape(y, p):
    return np.sum(np.abs(y - p)) / np.sum(np.abs(y)) * 100

pred_diff = xgb_clean.predict(X_test)
pred      = np.maximum(0, lag1_arr + pred_diff)
baseline  = wape(y_test, pred)
pers_wape = wape(y_test, lag1_arr)
print(f"Clean XGB WAPE:    {baseline:.2f}%")
print(f"Persistence WAPE:  {pers_wape:.2f}%")
print(f"n_test: {len(y_test)}")

SEEDS = list(range(200, 230))

# Individual feature permutation importance
gains = {}
print("\nIndividual feature permutation importances:")
for fi, fname in enumerate(DIFF_FEATURES):
    deltas = []
    for seed in SEEDS:
        rng = np.random.RandomState(seed)
        Xp  = X_test.copy()
        Xp[:, fi] = rng.permutation(Xp[:, fi])
        pdiff = xgb_clean.predict(Xp)
        ppred = np.maximum(0, lag1_arr + pdiff)
        deltas.append(wape(y_test, ppred) - baseline)
    gains[fname] = {"mean": float(np.mean(deltas)), "std": float(np.std(deltas)),
                    "ci_lo": float(np.percentile(deltas, 2.5)), "ci_hi": float(np.percentile(deltas, 97.5))}
    print(f"  {fname:20s}: +{gains[fname]['mean']:.2f}%  [{gains[fname]['ci_lo']:.2f}, {gains[fname]['ci_hi']:.2f}]")

total_pos = sum(v["mean"] for v in gains.values() if v["mean"] > 0)
print("\nGain shares (of total positive gain):")
for fname, g in gains.items():
    share = g["mean"] / total_pos * 100 if total_pos > 0 else 0
    gains[fname]["share_pct"] = share
    print(f"  {fname:20s}: {share:.1f}%")

# AR group permutation (lag_1_cases, lag_1_diff, lag_2_diff, cases_ma3)
AR_GROUP   = [f for f in ["lag_1_cases", "lag_1_diff", "lag_2_diff", "cases_ma3"] if f in DIFF_FEATURES]
AR_INDICES = [DIFF_FEATURES.index(f) for f in AR_GROUP]
group_deltas = []
for seed in SEEDS:
    rng  = np.random.RandomState(seed)
    Xp   = X_test.copy()
    perm = rng.permutation(len(y_test))
    for idx in AR_INDICES:
        Xp[:, idx] = Xp[:, idx][perm]
    pdiff = xgb_clean.predict(Xp)
    ppred = np.maximum(0, lag1_arr + pdiff)
    group_deltas.append(wape(y_test, ppred) - baseline)

group_mean   = float(np.mean(group_deltas))
group_share  = group_mean / total_pos * 100 if total_pos > 0 else 0
lag1_share   = gains.get("lag_1_cases", {}).get("share_pct", 0)
lag1_share_individual = gains.get("lag_1_cases", {}).get("mean", 0)
print(f"\nAR group ({AR_GROUP}):")
print(f"  Group delta WAPE: +{group_mean:.2f}% (share: {group_share:.1f}%)")
print(f"  lag_1_cases alone (mean delta): +{lag1_share_individual:.2f}% (share: {lag1_share:.1f}%)")
print(f"  Paper claims: lag_1 share = 55.0% (for Forecast), 51.2% (for Mortality)")

results = {
    "model":          "clean_retrained_xgb_on_wave1",
    "artifact":       "NOT the deployed forecast_cases_model.pkl",
    "n_train":        len(train_real),
    "n_test":         len(test_real),
    "baseline_wape":  baseline,
    "persistence_wape": pers_wape,
    "seeds":          SEEDS,
    "individual":     gains,
    "ar_group": {
        "features":    AR_GROUP,
        "mean_delta":  group_mean,
        "share_pct":   group_share,
    },
    "lag1_share_pct": lag1_share,
}

out_path = os.path.join(OUT_DIR, "clean_model_permutation_results.json")
with open(out_path, "w") as f:
    json.dump(results, f, indent=2)
print(f"\nSaved: {out_path}")
