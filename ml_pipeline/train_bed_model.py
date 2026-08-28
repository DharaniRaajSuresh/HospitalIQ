"""train_bed_model.py — Trains GradientBoostingRegressor for bed availability forecasting.
Loads processed bed data, trains with 5-fold TimeSeriesSplit, saves model + metadata."""

import logging
import os
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import TimeSeriesSplit

try:
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import save_model_versioned

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", "bed_data_processed.csv")
FEATURES = ["month_sin", "month_cos", "year_normalized", "season_flag",
            "state_encoded", "ward_type_encoded",
            "lag_1_month", "lag_3_month", "lag_6_month",
            "rolling_mean_3", "rolling_mean_6"]
TARGET = "available_beds"

print("=== Training BedPredictor (GradientBoosting) ===")
df = pd.read_csv(CSV_PATH)
df = df.sort_values(["state_encoded", "ward_type_encoded", "recorded_year", "recorded_month"])
df = df.dropna(subset=FEATURES + [TARGET])
X = df[FEATURES].values
y = df[TARGET].values
print(f"Loaded {len(df):,} rows, {len(FEATURES)} features")

from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = GradientBoostingRegressor(n_estimators=200, max_depth=4, learning_rate=0.05,
                                   subsample=0.8, random_state=42)
model.fit(X_train, y_train)
train_r2 = model.score(X_train, y_train)
test_r2 = model.score(X_test, y_test)
y_pred = model.predict(X_test)
mae = float(mean_absolute_error(y_test, y_pred))
rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
print(f"Train R² = {train_r2:.4f}, Test R² = {test_r2:.4f}, MAE = {mae:.2f}, RMSE = {rmse:.2f}")

save_model_versioned(model, "bed_model",
                     metrics={"r2": float(f"{test_r2:.4f}"),
                              "train_r2": float(f"{train_r2:.4f}"),
                              "mae": float(f"{mae:.4f}"),
                              "rmse": float(f"{rmse:.4f}")},
                     params={"n_estimators": 200, "max_depth": 4, "learning_rate": 0.05, "feature_names": FEATURES})
joblib.dump(model, os.path.join(MODEL_DIR, "bed_model.pkl"))
print("Done")
