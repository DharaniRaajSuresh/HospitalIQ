"""train_mortality_model.py — Trains XGBoost for death rate prediction.
Loads processed mortality data, trains with chronological split, saves model + metadata."""

import logging
import os
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import pandas as pd
from xgboost import XGBRegressor

try:
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import save_model_versioned

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", "mortality_data_processed.csv")
FEATURES = ["state_encoded", "district_encoded", "age_group_encoded",
            "cause_encoded", "year", "population_scaled",
            "month_sin", "month_cos", "season_flag",
            "lag_1_month", "lag_3_month", "lag_6_month",
            "rolling_mean_3", "rolling_mean_6"]
TARGET = "death_rate"

print("=== Training MortalityPredictor (XGBoost) ===")
df = pd.read_csv(CSV_PATH).dropna(subset=FEATURES + [TARGET])
df = df.sort_values(["state_encoded", "district_encoded", "year", "month"])
X = df[FEATURES].values
y = df[TARGET].values
print(f"Loaded {len(df):,} rows, {len(FEATURES)} features")

split = int(len(df) * 0.85)
X_train, X_test = X[:split], X[split:]
y_train, y_test = y[:split], y[split:]

model = XGBRegressor(n_estimators=200, max_depth=4, learning_rate=0.05,
                      subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
                      random_state=42, n_jobs=-1, verbosity=0)
model.fit(X_train, y_train)
train_r2 = model.score(X_train, y_train)
test_r2 = model.score(X_test, y_test)
print(f"Train R² = {train_r2:.4f}, Test R² = {test_r2:.4f}")

save_model_versioned(model, "mortality_xgb_model",
                     metrics={"r2": float(f"{test_r2:.4f}"), "train_r2": float(f"{train_r2:.4f}")},
                     feature_names=FEATURES, mlflow=None)
print("Done")
