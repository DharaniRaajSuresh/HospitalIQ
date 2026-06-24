import os, sys, logging, joblib, numpy as np, pandas as pd
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_DIR = "ml_pipeline/data/models"
os.makedirs(MODEL_DIR, exist_ok=True)

DISEASE_INFO = {
    "COVID-19": {"cfr": 3.0, "r0": 3.2}, "Ebola": {"cfr": 65.0, "r0": 1.8},
    "H1N1": {"cfr": 1.0, "r0": 1.6}, "SARS": {"cfr": 12.0, "r0": 2.8},
    "Nipah": {"cfr": 55.0, "r0": 1.5}, "Marburg": {"cfr": 55.0, "r0": 1.7},
}
DISEASES = list(DISEASE_INFO.keys())

def generate_training_data():
    rows = []
    for disease in DISEASES:
        di = DISEASE_INFO[disease]
        for severity in [0.5, 0.8, 1.0, 1.5, 2.0, 3.0]:
            for _ in range(80):
                cases = int(np.random.lognormal(mean=np.log(5000 * severity), sigma=0.6))
                cfr = di["cfr"] * (0.5 + np.random.random())
                deaths = int(cases * cfr / 100 * (0.7 + 0.6 * np.random.random()))
                r0 = di["r0"] * (0.85 + 0.3 * np.random.random())
                bed_demand = int(cases * 0.15 * (0.7 + 0.6 * np.random.random()))
                icu_demand = int(bed_demand * 0.25 * (0.7 + 0.6 * np.random.random()))
                rows.append({
                    "disease": disease, "total_cases": cases, "total_deaths": deaths,
                    "avg_r0": round(r0, 2), "avg_cfr": round(cfr, 2),
                    "total_bed_demand": bed_demand, "total_icu_demand": icu_demand,
                })
    return pd.DataFrame(rows)

df = generate_training_data()
disease_enc = {d: i for i, d in enumerate(sorted(DISEASES))}
state_enc = {"Kerala": 0}

df["disease_enc"] = df["disease"].map(disease_enc)
df["state_enc"] = 0

FEATURES = ["avg_r0", "avg_cfr", "total_cases", "total_deaths", "total_bed_demand", "total_icu_demand", "disease_enc", "state_enc"]

df["severity_idx"] = (
    df["total_cases"].rank(pct=True) * 0.15 +
    df["total_deaths"].rank(pct=True) * 0.35 +
    df["avg_r0"].rank(pct=True) * 0.05 +
    df["avg_cfr"].rank(pct=True) * 0.05 +
    df["total_bed_demand"].rank(pct=True) * 0.10 +
    df["total_icu_demand"].rank(pct=True) * 0.30
)
threshold = df["severity_idx"].quantile(0.6)
df["lockdown"] = (df["severity_idx"] >= threshold).astype(int)

df = df.sort_values(["disease", "total_deaths"])
split = int(len(df) * 0.8)
X = df[FEATURES].values
y = df["lockdown"].values
X_train, X_test, y_train, y_test = X[:split], X[split:], y[:split], y[split:]

scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

sample_weight = compute_sample_weight(class_weight="balanced", y=y_train)
model = XGBClassifier(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
                      colsample_bytree=0.8, reg_lambda=5.0, random_state=42, eval_metric="logloss")
model.fit(X_train, y_train, sample_weight=sample_weight)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]
acc = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_proba)

logger.info(f"Lockdown model — Test acc={acc:.3f}, AUC={auc:.3f}")
logger.info(f"\n{classification_report(y_test, y_pred, target_names=['No Lockdown', 'Lockdown'])}")

logger.info(f"Feature importances:")
for name, imp in sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1]):
    logger.info(f"  {name}: {imp:.3f}")

joblib.dump(model, os.path.join(MODEL_DIR, "lockdown_model.pkl"))
joblib.dump(scaler, os.path.join(MODEL_DIR, "lockdown_scaler.pkl"))
joblib.dump({
    "feature_names": FEATURES, "disease_encoding": disease_enc,
    "state_encoding": state_enc, "split_year": 2029,
    "severity_components": ["total_cases_pctl", "total_deaths_pctl", "avg_r0_pctl", "avg_cfr_pctl", "total_bed_demand_pctl", "total_icu_demand_pctl"],
    "model_type": "XGBClassifier", "description": "Lockdown classifier trained on severity percentiles",
}, os.path.join(MODEL_DIR, "lockdown_metadata.pkl"))
logger.info("Lockdown model saved!")
