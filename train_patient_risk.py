"""Train patient risk model on 200K patients × 6 viruses = 1.2M records.
Optimized: uses pandas read_sql + vectorized operations for memory efficiency."""
import sys, os, json, pickle, warnings, random
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import date, datetime
from sqlalchemy import create_engine

warnings.filterwarnings("ignore")

from backend.config import settings

random.seed(42)
np.random.seed(42)

MODEL_DIR = Path(__file__).parent / "ml_pipeline" / "data" / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(settings.database_url)

print("=== Training Patient Risk Model (200K × 6 viruses) ===")

conn = engine.raw_connection()

# Load all data via SQL for speed
print("Loading patients...", end=" ", flush=True)
t0 = datetime.now()
patients = pd.read_sql("SELECT id, age, blood_group, gender, pre_existing_conditions FROM patients", conn)
print(f"{len(patients):,} ({datetime.now()-t0})")

print("Loading vaccines...", end=" ", flush=True)
t0 = datetime.now()
vaccines = pd.read_sql("SELECT patient_id, virus_name, vaccination_date FROM vaccine_history", conn)
print(f"{len(vaccines):,} ({datetime.now()-t0})")

print("Loading travel...", end=" ", flush=True)
t0 = datetime.now()
travels = pd.read_sql("SELECT patient_id, travel_date, return_date FROM travel_history", conn)
print(f"{len(travels):,} ({datetime.now()-t0})")

print("Loading family...", end=" ", flush=True)
t0 = datetime.now()
families = pd.read_sql("SELECT patient_id, condition FROM family_history", conn)
print(f"{len(families):,} ({datetime.now()-t0})")

print("Loading viruses...", end=" ", flush=True)
t0 = datetime.now()
viruses = pd.read_sql("SELECT * FROM virus_registry", conn)
print(f"{len(viruses):,} ({datetime.now()-t0})")

conn.close()
engine.dispose()

# Aggregate per patient (vectorized)
today = date.today()

# Vaccine summary — convert dates first
vaccines["v_date"] = pd.to_datetime(vaccines["vaccination_date"], errors="coerce").dt.date
v_summ = vaccines.groupby("patient_id").agg(
    num_doses=("patient_id", "count"),
    has_covid_vaccine=("virus_name", lambda x: int(any("covid" in str(v).lower() for v in x))),
    last_vaccine_days=("v_date", lambda x: int(max(0, min((today - d).days for d in x if d is not None))))
).reset_index()
all_pids = patients["id"].values
v_summ_full = pd.DataFrame({"patient_id": all_pids}).merge(v_summ, on="patient_id", how="left").fillna({"num_doses": 0, "has_covid_vaccine": 0, "last_vaccine_days": 999})
v_summ_full["last_vaccine_days"] = v_summ_full["last_vaccine_days"].clip(0, 999).astype(int)

# Travel summary
if len(travels) > 0:
    travels["return_dt"] = pd.to_datetime(travels["return_date"], errors="coerce").dt.date
    travels["travel_dt"] = pd.to_datetime(travels["travel_date"], errors="coerce").dt.date
    def is_recent(row):
        rd = row["return_dt"]
        td = row["travel_dt"]
        if rd is not None and (today - rd).days <= 30:
            return 1
        if td is not None and (today - td).days <= 60:
            return 1
        return 0
    travels["recent"] = travels.apply(is_recent, axis=1)
    t_summ = travels.groupby("patient_id").agg(total_trips=("patient_id", "count"), recent_30d=("recent", "max")).reset_index()
else:
    t_summ = pd.DataFrame(columns=["patient_id", "total_trips", "recent_30d"])
t_summ_full = pd.DataFrame({"patient_id": all_pids}).merge(t_summ, on="patient_id", how="left").fillna({"total_trips": 0, "recent_30d": 0})

# Family summary
high_risk_fam_conds = {"diabetes", "cardiac", "cancer", "stroke", "renal disease"}
if len(families) > 0:
    families["is_high_risk"] = families["condition"].str.lower().isin(high_risk_fam_conds).astype(int)
    f_summ = families.groupby("patient_id").agg(
        high_risk_count=("is_high_risk", "sum"),
        total_conditions=("patient_id", "count")
    ).reset_index()
else:
    f_summ = pd.DataFrame(columns=["patient_id", "high_risk_count", "total_conditions"])
f_summ_full = pd.DataFrame({"patient_id": all_pids}).merge(f_summ, on="patient_id", how="left").fillna({"high_risk_count": 0, "total_conditions": 0})

# Pre-existing conditions per patient
high_risk_conds = {"diabetes", "cardiac", "cancer", "hypertension", "asthma", "renal", "obesity"}
def count_conditions(s):
    if pd.isna(s) or not s:
        return 0
    return sum(1 for c in str(s).lower().split(",") if c.strip() in high_risk_conds)
patients["num_preexisting"] = patients["pre_existing_conditions"].apply(count_conditions)

# Feature encodings
blood_map = {"A+": 0, "A-": 1, "B+": 2, "B-": 3, "AB+": 4, "AB-": 5, "O+": 6, "O-": 7}
patients["blood_group_code"] = patients["blood_group"].map(blood_map).fillna(4).astype(int)
patients["gender_male"] = (patients["gender"].str.lower() == "male").astype(int)
patients["age_norm"] = (patients["age"].fillna(40) / 100.0).astype(np.float32)

# Build the cross product: patients × viruses
print(f"Building {len(patients):,} × {len(viruses):,} feature matrix...", end=" ", flush=True)
t0 = datetime.now()

# Create cross-product using merge
patients["_key"] = 1
viruses["_key"] = 1
cross = patients.merge(viruses, on="_key").drop(columns=["_key"])
cross = cross.drop(columns=["id_y", "created_at", "notes", "transmission_mode", "treatment_available"])  # drop unused cols
cross = cross.rename(columns={"id_x": "patient_id"})

# Merge with summaries
cross = cross.merge(v_summ_full, on="patient_id", suffixes=("", "_agg"))
cross = cross.merge(t_summ_full, on="patient_id", suffixes=("", "_agg"))
cross = cross.merge(f_summ_full, on="patient_id", suffixes=("", "_agg"))

print(f"{len(cross):,} records ({datetime.now()-t0})")

# --- Feature engineering ---
print("Engineering features...", end=" ", flush=True)
t0 = datetime.now()

# Age-based risk components
age = cross["age_norm"].values
num_pre = cross["num_preexisting"].values
fam_high = cross["high_risk_count"].values
num_doses = cross["num_doses"].values
has_covid = cross["has_covid_vaccine"].values
last_vax = (np.clip(cross["last_vaccine_days"].values, 0, 999) / 1000.0).astype(np.float32)
recent_travel = cross["recent_30d"].values
num_trips = cross["total_trips"].values
fam_total = cross["total_conditions"].values
virus_fatality = cross["fatality_rate"].fillna(0.05).values
virus_repro = cross["reproductive_rate"].fillna(1.5).values
vaccine_avail = cross["vaccine_available"].fillna(0).values
vaccine_eff = cross["vaccine_effectiveness"].fillna(0).values

age_factor = age * 0.6 + num_pre * 0.08 + fam_high * 0.04
age_mask_60 = age * 100 > 60
age_mask_75 = age * 100 > 75
age_factor[age_mask_60] += 0.15
age_factor[age_mask_75] += 0.10

vaccine_protection = num_doses * 0.08 + has_covid * 0.05 + vaccine_avail * vaccine_eff * 0.3
vaccine_protection = np.clip(vaccine_protection, 0, 0.6)

travel_risk = recent_travel * 0.1 + num_trips * 0.01
travel_risk = np.clip(travel_risk, 0, 0.2)

virus_risk = virus_fatality * 0.3 + np.clip(virus_repro / 5.0, 0, 0.6) * 0.2

raw_risk = age_factor + virus_risk + travel_risk - vaccine_protection
raw_risk = np.clip(raw_risk + np.random.normal(0, 0.03, raw_risk.shape), 0.01, 0.99)

hosp_prob = raw_risk * (0.5 + virus_fatality * 2.5)
hosp_prob = np.clip(hosp_prob + np.random.normal(0, 0.02, hosp_prob.shape), 0.01, 0.99)

age_mort = np.ones_like(age)
age_mort[age_mask_60] = 1.5
age_mort[age_mask_75] = 2.0
mortality_prob = hosp_prob * 0.08 * age_mort * (1 + virus_fatality * 5)
mortality_prob = np.clip(mortality_prob + np.random.normal(0, 0.01, mortality_prob.shape), 0.001, 0.95)

# Build final arrays
feature_cols = ["age","blood_group","gender_male","num_preexisting","num_doses","has_covid_vaccine",
                "last_vaccine_days","recent_travel","num_trips","fam_high_risk","fam_total",
                "virus_fatality","virus_reproductive","vaccine_available","vaccine_effectiveness"]
target_cols = ["risk_score","hospitalization_prob","mortality_prob"]

n = len(cross)
X = np.zeros((n, len(feature_cols)), dtype=np.float32)
X[:, 0] = age
X[:, 1] = cross["blood_group_code"].values
X[:, 2] = cross["gender_male"].values
X[:, 3] = num_pre
X[:, 4] = num_doses
X[:, 5] = has_covid
X[:, 6] = last_vax
X[:, 7] = recent_travel
X[:, 8] = num_trips
X[:, 9] = fam_high
X[:, 10] = fam_total
X[:, 11] = virus_fatality
X[:, 12] = virus_repro
X[:, 13] = vaccine_avail
X[:, 14] = vaccine_eff

y = np.column_stack([raw_risk, hosp_prob, mortality_prob]).astype(np.float32)

print(f"{n:,} × {len(feature_cols)} features ({datetime.now()-t0})")

# Train with RandomForest (reduced config for 1.2M records)
print("Training models (n_estimators=50, max_depth=10)...")
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

models = {}
for i, target in enumerate(target_cols):
    print(f"Training {target} ({y_train.shape[0]:,} samples)...", end=" ", flush=True)
    t0 = datetime.now()
    rf = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42, n_jobs=-1, verbose=0)
    rf.fit(X_train, y_train[:, i])
    train_score = rf.score(X_train, y_train[:, i])
    test_score = rf.score(X_test, y_test[:, i])
    models[target] = rf
    print(f"R2 train={train_score:.4f} test={test_score:.4f} ({datetime.now()-t0})")

# Save
model_path = MODEL_DIR / "patient_risk_model.pkl"
with open(model_path, "wb") as f:
    pickle.dump(models, f)

metadata = {
    "feature_names": feature_cols, "target_names": target_cols,
    "n_patients": len(patients), "n_records": len(cross),
    "n_estimators": 50, "max_depth": 10,
    "model_type": "RandomForestRegressor",
    "blood_group_map": blood_map,
    "high_risk_conditions": list(high_risk_conds),
    "blood_groups": list(blood_map.keys()),
    "model_version": datetime.now().strftime("%Y%m%d_%H%M%S"),
}
meta_path = MODEL_DIR / "patient_risk_metadata.pkl"
with open(meta_path, "wb") as f:
    pickle.dump(metadata, f)

print(f"\nModel saved: {model_path}")
print(f"Metadata saved: {meta_path}")
print("Done!")
