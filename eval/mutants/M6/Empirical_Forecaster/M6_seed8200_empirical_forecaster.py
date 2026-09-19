"""
eval/baselines/empirical_forecaster.py
Standalone baseline pipeline: Empirical time-series outbreak surveillance forecaster.
Trained on Wave-1 state-level monthly surveillance data with strict chronological train/test split.
"""
import os, math, pickle
import numpy as np
import pandas as pd
from xgboost import XGBRegressor

HOSPI = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def train_and_evaluate(random_state=42):
    csv_path = os.path.join(HOSPI, "ml_pipeline", "data", "raw", "outbreak_real.csv")
    df = pd.read_csv(csv_path)
    covid = df[(df["disease"] == "COVID-19") & (df["source"] == "COVID19-India API")].copy()
    covid["date"] = pd.to_datetime(covid["date"])
    covid = covid.sort_values(["state", "date"]).reset_index(drop=True)

    records = []
    for state, g in covid.groupby("state"):
        g = g.sort_values("date").reset_index(drop=True)
        if len(g) < 4:
            continue
        for i in range(3, len(g)):
            row = g.iloc[i]
            l1, l2, l3 = g.iloc[i-1], g.iloc[i-2], g.iloc[i-3]
            m = row["date"].month
            records.append({
                "date": str(row["date"].date()),
                "state": state,
                "month_sin": math.sin(2 * math.pi * m / 12),
                "month_cos": math.cos(2 * math.pi * m / 12),
                "lag_1_cases": float(l1["confirmed_cases"]),
                "lag_2_cases": float(l2["confirmed_cases"]),
                "lag_3_cases": float(l3["confirmed_cases"]),
                "cases_ma3": float((l1["confirmed_cases"] + l2["confirmed_cases"] + l3["confirmed_cases"]) / 3.0),
                "target_cases": float(row["confirmed_cases"])
            })

    feat_df = pd.DataFrame(records)
    feat_cols = ["month_sin", "month_cos", "lag_1_cases", "lag_2_cases", "lag_3_cases", "cases_ma3"]

    # Strict chronological split: train < 2021-04-01, test >= 2021-04-01
    train = feat_df[feat_df["date"] < "2021-04-01"].copy()
    test = feat_df[feat_df["date"] >= "2021-04-01"].copy()

    X_train, y_train = train[feat_cols].values, train["target_cases"].values
    X_test, y_test = test[feat_cols].values, test["target_cases"].values

    model = XGBRegressor(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=random_state, verbosity=0)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    wape = np.sum(np.abs(y_test - y_pred)) / max(np.sum(np.abs(y_test)), 1e-5) * 100

    meta = {
        "pipeline": "Empirical_Surveillance_Forecaster",
        "feature_names": feat_cols,
        "n_features_in_": len(feat_cols),
        "test_wape": float(wape),
        "n_train": len(train),
        "n_test": len(test)
    }

    out_dir = os.path.join(os.path.dirname(__file__), "artifacts")
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "forecaster_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(out_dir, "forecaster_metadata.pkl"), "wb") as f:
        pickle.dump(meta, f)

    return wape

if __name__ == "__main__":
    wape = train_and_evaluate()
    print(f"Empirical Forecaster Baseline: Test WAPE = {wape:.2f}%")


# [M6 MUTATION seed=8200]
import pickle as _m6p, os as _m6o
_m6f = [f for f in _m6o.listdir('.') if 'metadata' in f and f.endswith('.pkl')]
if _m6f:
    _m6m = _m6p.load(open(_m6f[0], "rb"))
    if isinstance(_m6m, dict):
        _m6p.dump(list(_m6m.items()), open(_m6f[0], "wb"))