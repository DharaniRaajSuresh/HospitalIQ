"""
train_patient_risk.py — Trains individual patient pandemic risk models.
Predicts risk_score, hospitalization_prob, mortality_prob from patient
demographics, medical history, and virus characteristics.

Uses 3 separate RandomForestRegressors (one per target), stored as a dict
for backward compatibility with PatientRiskPredictor.
"""

import os, sys, logging, pickle
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from ml_utils import MODEL_DIR
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from ml_utils import MODEL_DIR

MODELS_DIR = MODEL_DIR
os.makedirs(MODELS_DIR, exist_ok=True)

FEATURE_NAMES = [
    "age", "blood_group", "gender_male",
    "num_preexisting", "num_doses", "has_covid_vaccine",
    "last_vaccine_days", "recent_travel", "num_trips",
    "fam_high_risk", "fam_total",
    "virus_fatality", "virus_reproductive",
    "vaccine_available", "vaccine_effectiveness",
]

TARGET_NAMES = ["risk_score", "hospitalization_prob", "mortality_prob"]

BLOOD_GROUP_MAP = {"A+": 0, "A-": 1, "B+": 2, "B-": 3, "AB+": 4, "AB-": 5, "O+": 6, "O-": 7}
HIGH_RISK_CONDITIONS = [
    "Diabetes", "Hypertension", "Asthma", "Heart Disease",
    "Kidney Disease", "Liver Disease", "Immunocompromised", "Obesity",
]


def compute_risk_labels(row):
    age = row.get("age", 30)
    num_preexisting = row.get("num_preexisting", 0)
    num_doses = row.get("num_doses", 0)
    last_vaccine_days = row.get("last_vaccine_days", 9999)
    recent_travel = row.get("recent_travel", 0)
    num_trips = row.get("num_trips", 0)
    fam_high_risk = row.get("fam_high_risk", 0)
    virus_fatality = row.get("virus_fatality", 0.05)
    virus_reproductive = row.get("virus_reproductive", 2.0)
    vaccine_available = row.get("vaccine_available", 1)
    vaccine_effectiveness = row.get("vaccine_effectiveness", 0.8)

    # Age risk
    age_risk = min(1.0, max(0, age - 10) / 80)

    # Pre-existing conditions
    condition_risk = min(1.0, num_preexisting / 5)

    # Vaccination protection
    if vaccine_available and vaccine_effectiveness > 0:
        dose_protection = min(1.0, num_doses * 0.4)
        waning = max(0, 1 - last_vaccine_days / 730)
        vax_protection = dose_protection * waning * vaccine_effectiveness
    else:
        vax_protection = 0

    # Travel exposure
    travel_risk = min(1.0, recent_travel * (1 + num_trips * 0.2))

    # Family history
    family_risk = min(1.0, fam_high_risk * 0.4)

    # Virus virulence
    virus_risk = min(1.0, virus_fatality * 5 + (virus_reproductive - 1) * 0.3)

    # Composite risk score (0-1)
    risk_score = min(1.0, (
        age_risk * 0.25 +
        condition_risk * 0.20 +
        travel_risk * 0.10 +
        family_risk * 0.10 +
        virus_risk * 0.20 +
        (1 - vax_protection) * 0.15
    ))

    # Hospitalization probability (~0.1 to 0.9)
    hosp_prob = min(0.9, max(0.1, risk_score * 0.8 + condition_risk * 0.15 + age_risk * 0.05))

    # Mortality probability (~0.01 to 0.5)
    mort_prob = min(0.5, max(0.01, risk_score * virus_fatality * 2 + condition_risk * 0.1))

    return risk_score, hosp_prob, mort_prob


def generate_synthetic_data(n_patients=5000, n_viruses=6):
    np.random.seed(42)
    viruses = [
        {"name": "COVID-19", "fatality": 0.03, "reproductive": 3.2, "vaccine": True, "vax_eff": 0.85},
        {"name": "Ebola", "fatality": 0.60, "reproductive": 2.0, "vaccine": False, "vax_eff": 0},
        {"name": "H1N1", "fatality": 0.01, "reproductive": 1.5, "vaccine": True, "vax_eff": 0.70},
        {"name": "Marburg", "fatality": 0.50, "reproductive": 1.8, "vaccine": False, "vax_eff": 0},
        {"name": "Nipah", "fatality": 0.55, "reproductive": 1.2, "vaccine": False, "vax_eff": 0},
        {"name": "SARS", "fatality": 0.12, "reproductive": 3.0, "vaccine": True, "vax_eff": 0.75},
    ]
    blood_groups = list(BLOOD_GROUP_MAP.keys())

    records = []
    for pid in range(n_patients):
        patient = {
            "age": np.random.randint(1, 90),
            "blood_group": BLOOD_GROUP_MAP[np.random.choice(blood_groups)],
            "gender_male": np.random.randint(0, 2),
            "num_preexisting": np.random.choice([0, 0, 0, 1, 1, 2, 3]),
            "num_doses": np.random.choice([0, 0, 1, 1, 2, 2, 3]),
            "has_covid_vaccine": np.random.randint(0, 2),
            "last_vaccine_days": np.random.randint(30, 730) if np.random.random() > 0.2 else 9999,
            "recent_travel": np.random.randint(0, 2),
            "num_trips": np.random.randint(0, 5),
            "fam_high_risk": np.random.randint(0, 4),
            "fam_total": np.random.randint(2, 8),
        }

        for virus in viruses:
            row = {**patient,
                "virus_fatality": virus["fatality"],
                "virus_reproductive": virus["reproductive"],
                "vaccine_available": 1 if virus["vaccine"] else 0,
                "vaccine_effectiveness": virus["vax_eff"],
            }
            rs, hp, mp = compute_risk_labels(row)
            records.append({
                **row,
                "risk_score": rs,
                "hospitalization_prob": hp,
                "mortality_prob": mp,
            })

    df = pd.DataFrame(records)
    logger.info(f"Generated {len(df)} training records from {n_patients} patients x {n_viruses} viruses")
    return df


def train_patient_risk_models():
    logger.info("=" * 60)
    logger.info("PATIENT RISK: Individual Risk Model Training")
    logger.info("=" * 60)

    df = generate_synthetic_data(n_patients=5000)

    X = df[FEATURE_NAMES].values
    targets = {}
    for t in TARGET_NAMES:
        targets[t] = df[t].values

    X_train, X_test, y_train, y_test = {}, {}, {}, {}
    splits = {}
    for t in TARGET_NAMES:
        X_train[t], X_test[t], y_train[t], y_test[t] = train_test_split(
            X, targets[t], test_size=0.2, random_state=42
        )

    models = {}
    metrics = {}
    for t in TARGET_NAMES:
        logger.info(f"Training {t}...")
        model = RandomForestRegressor(
            n_estimators=100, max_depth=10,
            min_samples_leaf=5, random_state=42, n_jobs=-1,
        )
        model.fit(X_train[t], y_train[t])

        train_r2 = model.score(X_train[t], y_train[t])
        test_r2 = model.score(X_test[t], y_test[t])
        logger.info(f"  {t}: Train R²={train_r2:.4f}, Test R²={test_r2:.4f}")
        models[t] = model
        metrics[t] = {"train_r2": float(train_r2), "test_r2": float(test_r2)}

    # Save as dict (3 separate models — matches existing predictor)
    output_path = os.path.join(MODELS_DIR, "patient_risk_model.pkl")
    with open(output_path, "wb") as f:
        pickle.dump(models, f)

    metadata = {
        "feature_names": FEATURE_NAMES,
        "target_names": TARGET_NAMES,
        "n_patients": 5000,
        "n_records": len(df),
        "n_estimators": 100,
        "max_depth": 10,
        "model_type": "random_forest",
        "blood_group_map": BLOOD_GROUP_MAP,
        "high_risk_conditions": HIGH_RISK_CONDITIONS,
        "blood_groups": list(BLOOD_GROUP_MAP.keys()),
        "model_version": "v1",
    }
    meta_path = os.path.join(MODELS_DIR, "patient_risk_metadata.pkl")
    with open(meta_path, "wb") as f:
        pickle.dump(metadata, f)

    logger.info(f"Saved model ({len(models)} targets) to {output_path}")
    logger.info(f"Saved metadata to {meta_path}")
    logger.info("Patient risk training complete!")
    return metrics


if __name__ == "__main__":
    train_patient_risk_models()
