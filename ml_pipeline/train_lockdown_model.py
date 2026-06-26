import logging
import os
import sqlite3
import sys

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "ml_pipeline/data/models"
os.makedirs(MODEL_DIR, exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ml_pipeline", "data", "hospitaliq.db")

logger.info("Loading real outbreak data from DB...")
conn = sqlite3.connect(DB_PATH)

# Aggregate by (disease, state, year) — one sample per scenario
df = pd.read_sql_query("""
    SELECT
        disease,
        state,
        year,
        SUM(confirmed_cases) as total_cases,
        SUM(deaths) as total_deaths,
        SUM(bed_demand) as total_bed_demand,
        SUM(icu_demand) as total_icu_demand,
        AVG(reproduction_rate) as avg_r0,
        AVG(case_fatality_rate) as avg_cfr
    FROM pandemic_outbreak
    GROUP BY disease, state, year
    ORDER BY disease, state, year
""", conn)
conn.close()

logger.info(f"Loaded {len(df)} samples across {df['disease'].nunique()} diseases, "
            f"{df['state'].nunique()} states, years {df['year'].min()}-{df['year'].max()}")

# Severity score within each disease so high-CFR diseases get fair representation
df["severity_idx"] = (
    df.groupby("disease")["total_deaths"].rank(pct=True) * 0.35 +
    df.groupby("disease")["avg_cfr"].rank(pct=True) * 0.25 +
    df.groupby("disease")["total_cases"].rank(pct=True) * 0.10 +
    df.groupby("disease")["avg_r0"].rank(pct=True) * 0.05 +
    df.groupby("disease")["total_bed_demand"].rank(pct=True) * 0.10 +
    df.groupby("disease")["total_icu_demand"].rank(pct=True) * 0.15
)
# Label: top 30% severity within each disease → lockdown
threshold = df["severity_idx"].quantile(0.70)
df["lockdown"] = (df["severity_idx"] >= threshold).astype(int)
lockdown_by_disease = df.groupby("disease")["lockdown"].mean()
logger.info(f"Lockdown rate by disease: {lockdown_by_disease.to_dict()}")
lockdown_rate = df["lockdown"].mean()
logger.info(f"Lockdown threshold at severity {threshold:.3f}, "
            f"{lockdown_rate*100:.1f}% of samples labelled lockdown")

# Check: which disease/state/year combos get lockdown?
logger.info("Sample lockdown decisions (first 20):")
for _, r in df.sort_values(["year", "disease", "state"]).head(20).iterrows():
    logger.info(f"  {r['disease']} {r['year']} {r['state']:20s} → "
                f"{'LOCKDOWN' if r['lockdown'] else 'unlock'} "
                f"(deaths={r['total_deaths']}, r0={r['avg_r0']:.2f})")

FEATURES = ["avg_r0", "avg_cfr", "total_cases", "total_deaths",
            "total_bed_demand", "total_icu_demand"]

X = df[FEATURES].values
y = df["lockdown"].values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
model = XGBClassifier(
    n_estimators=200, max_depth=4, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8, reg_lambda=5.0,
    random_state=42, eval_metric="logloss",
)
model.fit(X_train, y_train, sample_weight=sample_weight)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]
acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

logger.info(f"Lockdown model — Test acc={acc:.3f}, AUC={auc:.3f}")
logger.info(f"\n{classification_report(y_test, y_pred, target_names=['No Lockdown', 'Lockdown'])}")

logger.info("Feature importances:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    logger.info(f"  {name}: {imp:.3f}")

joblib.dump(model, os.path.join(MODEL_DIR, "lockdown_model.pkl"))
joblib.dump(scaler, os.path.join(MODEL_DIR, "lockdown_scaler.pkl"))
joblib.dump({
    "feature_names": FEATURES,
    "training_samples": len(df),
    "lockdown_rate": float(lockdown_rate),
    "source": "real pandemic_outbreak data",
    "model_type": "XGBClassifier",
    "description": "Lockdown classifier trained on real outbreak data — no disease/state encodings",
}, os.path.join(MODEL_DIR, "lockdown_metadata.pkl"))

logger.info("Lockdown model saved successfully using real data!")
