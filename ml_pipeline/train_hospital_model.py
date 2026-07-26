"""train_hospital_model.py — Trains RandomForest for hospital success rate ranking.
Loads processed hospital outcomes, encodes categoricals, trains + saves model."""

import logging
import os
import sys
import warnings

logging.disable(logging.CRITICAL)
warnings.filterwarnings("ignore")
os.environ["SKIP_DB_INIT"] = "1"

import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

try:
    from ml_utils import MODEL_DIR, save_model_versioned, setup_mlflow
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import save_model_versioned

CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "processed", "hospital_outcomes_processed.csv")
FEATURES = ["total_beds", "icu_beds", "avg_stay_days", "specialist_count"]
CAT_FEATURES = ["hospital_type", "disease", "state", "accreditation"]
TARGET = "success_rate"

print("=== Training HospitalPredictor (RandomForest) ===")
df = pd.read_csv(CSV_PATH).dropna(subset=[TARGET])
for col in CAT_FEATURES:
    if col in df.columns:
        df[f"{col}_encoded"] = pd.factorize(df[col])[0]

feature_cols = FEATURES + [f"{c}_encoded" for c in CAT_FEATURES if f"{c}_encoded" in df.columns]
df = df.dropna(subset=feature_cols)
X = df[feature_cols].values
y = df[TARGET].values
print(f"Loaded {len(df):,} rows, {len(feature_cols)} features")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
train_r2 = model.score(X_train, y_train)
test_r2 = model.score(X_test, y_test)
print(f"Train R² = {train_r2:.4f}, Test R² = {test_r2:.4f}")

save_model_versioned(model, "hospital_rf_model",
                     metrics={"r2": float(f"{test_r2:.4f}"), "train_r2": float(f"{train_r2:.4f}")},
                     feature_names=feature_cols, mlflow=None)
print("Done")
