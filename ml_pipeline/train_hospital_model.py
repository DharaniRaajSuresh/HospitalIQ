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

TYPE_ENCODING = {"Govt": 0, "Private": 1, "Trust": 2, "NGO": 3}
ACCRED_ENCODING = {"NABH": 3, "JCI": 3, "ISO": 2, "None": 1}
DISEASES = ["Cardiac", "Diabetes", "Dengue", "Tuberculosis",
            "Pneumonia", "Cancer", "Stroke", "Hepatitis", "Malaria", "Typhoid"]
DISEASE_ENCODING = {d: i for i, d in enumerate(sorted(DISEASES))}

FEATURE_COLS = [
    "hospital_type_encoded", "disease_encoded", "state_encoded",
    "total_beds", "icu_beds", "avg_stay_days",
    "specialist_count", "accreditation_encoded"
]
TARGET = "success_rate"

print("=== Training HospitalPredictor (RandomForest, 8 features) ===")
df = pd.read_csv(CSV_PATH).dropna(subset=[TARGET])

df["hospital_type_encoded"] = df["hospital_type"].map(TYPE_ENCODING).fillna(0).astype(int)
df["disease_encoded"] = df["disease"].map(DISEASE_ENCODING).fillna(0).astype(int)
df["accreditation_encoded"] = df["accreditation"].map(ACCRED_ENCODING).fillna(1).astype(int)
if "state_encoded" not in df.columns:
    df["state_encoded"] = pd.factorize(df["state"])[0]

df = df.dropna(subset=FEATURE_COLS)
X = df[FEATURE_COLS].values
y = df[TARGET].values
print(f"Loaded {len(df):,} rows, {len(FEATURE_COLS)} features: {FEATURE_COLS}")

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
model.fit(X_train, y_train)
train_r2 = model.score(X_train, y_train)
test_r2 = model.score(X_test, y_test)
print(f"Train R² = {train_r2:.4f}, Test R² = {test_r2:.4f}")

save_model_versioned(model, "hospital_rf_model",
                     metrics={"r2": float(f"{test_r2:.4f}"), "train_r2": float(f"{train_r2:.4f}")},
                     params={"n_estimators": 100, "max_depth": 10, "feature_names": FEATURE_COLS})
joblib.dump(model, os.path.join(MODEL_DIR, "hospital_rf_model.pkl"))
print("Done")
