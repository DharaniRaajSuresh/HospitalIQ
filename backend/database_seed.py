import sys
import os
import math
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from backend.database import SessionLocal, init_db, engine
from backend.models import Base, User, HospitalBed, MortalityRecord, HospitalOutcome, PatientAdmission
from backend.auth import get_password_hash

def seed_db():
    print("=" * 60)
    print("HospitalIQ v2.0 - Seeding Database")
    print("=" * 60)

    # Initialize tables
    init_db()

    session = SessionLocal()
    
    try:
        # 1. Seed Admin User
        admin_email = "admin@hospitaliq.com"
        existing_admin = session.query(User).filter_by(email=admin_email).first()
        if not existing_admin:
            hashed_password = get_password_hash("Admin@123")
            admin = User(
                email=admin_email,
                hashed_password=hashed_password,
                full_name="HospitalIQ Admin",
                role="admin",
                is_active=True
            )
            session.add(admin)
            session.commit()
            print("[SUCCESS] Seeded default admin user: admin@hospitaliq.com / Admin@123")
        else:
            print("[INFO] Admin user already exists, skipping user seed.")

        # Data path config
        raw_dir = Path(__file__).parent.parent / "ml_pipeline" / "data" / "raw"
        
        # 2. Seed Hospital Beds
        beds_csv = raw_dir / "beds_raw.csv"
        if beds_csv.exists():
            print("Seeding hospital_beds from beds_raw.csv...")
            session.query(HospitalBed).delete()
            session.commit()

            BATCH_SIZE = 50000
            df = pd.read_csv(beds_csv)
            total_rows = len(df)
            print(f"  Loading {total_rows:,} records in batches of {BATCH_SIZE:,}...")
            for start in range(0, total_rows, BATCH_SIZE):
                batch_df = df.iloc[start:start + BATCH_SIZE]
                records = []
                for _, row in batch_df.iterrows():
                    records.append(HospitalBed(
                        state=row["state"],
                        district=row.get("district", None),
                        hospital_name=row.get("hospital_name", None),
                        ward_type=row["ward_type"],
                        total_beds=int(row["total_beds"]),
                        available_beds=int(row["available_beds"]),
                        occupancy_rate=float(row["occupancy_rate"]),
                        recorded_month=int(row["recorded_month"]),
                        recorded_year=int(row["recorded_year"])
                    ))
                session.bulk_save_objects(records)
                session.commit()
                pct = min(100, (start + BATCH_SIZE) / total_rows * 100)
                print(f"  {min(start + BATCH_SIZE, total_rows):,}/{total_rows:,} ({pct:.0f}%)")
            print(f"[SUCCESS] Seeded hospital_beds table: {total_rows:,} rows inserted.")
        else:
            print(f"[WARNING] Beds raw data not found at {beds_csv}, skipping.")

        # 3. Seed Mortality Records
        mortality_csv = raw_dir / "mortality_raw.csv"
        if mortality_csv.exists():
            print("Seeding mortality_records from mortality_raw.csv...")
            session.query(MortalityRecord).delete()
            session.commit()

            BATCH_SIZE = 50000
            df = pd.read_csv(mortality_csv)
            total_rows = len(df)
            print(f"  Loading {total_rows:,} records in batches of {BATCH_SIZE:,}...")
            for start in range(0, total_rows, BATCH_SIZE):
                batch_df = df.iloc[start:start + BATCH_SIZE]
                records = []
                for _, row in batch_df.iterrows():
                    records.append(MortalityRecord(
                        state=row["state"],
                        district=row["district"],
                        year=int(row["year"]),
                        month=int(row.get("month", 6)),
                        age_group=row.get("age_group", None),
                        cause_of_death=row.get("cause_of_death", None),
                        death_count=int(row["death_count"]),
                        death_rate=float(row["death_rate"]),
                        population=int(row["population"]),
                        risk_cluster=row.get("risk_cluster", "Moderate")
                    ))
                session.bulk_save_objects(records)
                session.commit()
                pct = min(100, (start + BATCH_SIZE) / total_rows * 100)
                print(f"  {min(start + BATCH_SIZE, total_rows):,}/{total_rows:,} ({pct:.0f}%)")
            print(f"[SUCCESS] Seeded mortality_records table: {total_rows:,} rows inserted.")
        else:
            print(f"[WARNING] Mortality raw data not found at {mortality_csv}, skipping.")

        # 4. Seed Hospital Outcomes
        hospitals_csv = raw_dir / "hospital_outcomes_raw.csv"
        if hospitals_csv.exists():
            print("Seeding hospital_outcomes from hospital_outcomes_raw.csv...")
            session.query(HospitalOutcome).delete()
            session.commit()

            df = pd.read_csv(hospitals_csv)
            records = []
            for _, row in df.iterrows():
                records.append(HospitalOutcome(
                    hospital_id=row.get("hospital_id", None),
                    hospital_name=row["hospital_name"],
                    state=row["state"],
                    district=row.get("district", None),
                    hospital_type=row.get("hospital_type", None),
                    disease=row["disease"],
                    total_cases=int(row["total_cases"]),
                    success_count=int(row["success_count"]),
                    failure_count=int(row["failure_count"]),
                    success_rate=float(row["success_rate"]),
                    avg_stay_days=float(row["avg_stay_days"]),
                    total_beds=int(row["total_beds"]),
                    icu_beds=int(row.get("icu_beds", 0)),
                    specialist_count=int(row.get("specialist_count", 0)),
                    accreditation=None if (isinstance(row.get("accreditation"), float) and math.isnan(row["accreditation"])) else row.get("accreditation", None),
                    hospital_score=float(row.get("hospital_score", 0.0)),
                    rating=float(row.get("rating", 0.0))
                ))
            session.bulk_save_objects(records)
            session.commit()
            print(f"[SUCCESS] Seeded hospital_outcomes table: {len(records)} rows inserted.")
        else:
            print(f"[WARNING] Hospital outcomes raw data not found at {hospitals_csv}, skipping.")

        # 5. Seed Patient Admissions
        admissions_csv = raw_dir / "patient_admissions_raw.csv"
        if admissions_csv.exists():
            print("Seeding patient_admissions from patient_admissions_raw.csv...")
            session.query(PatientAdmission).delete()
            session.commit()

            BATCH_SIZE = 50000
            df = pd.read_csv(admissions_csv)
            total_rows = len(df)
            print(f"  Loading {total_rows:,} records in batches of {BATCH_SIZE:,}...")
            for start in range(0, total_rows, BATCH_SIZE):
                batch_df = df.iloc[start:start + BATCH_SIZE]
                records = []
                for _, row in batch_df.iterrows():
                    adm_date = datetime.strptime(row["admission_date"], "%Y-%m-%d").date()
                    dis_date = datetime.strptime(row["discharge_date"], "%Y-%m-%d").date() if not pd.isna(row.get("discharge_date")) else None
                    records.append(PatientAdmission(
                        patient_id=row.get("patient_id", None),
                        admission_date=adm_date,
                        discharge_date=dis_date,
                        hospital_id=row.get("hospital_id", None),
                        hospital_name=row.get("hospital_name", None),
                        state=row.get("state", None),
                        disease=row.get("disease", None),
                        age_group=row.get("age_group", None),
                        gender=row.get("gender", None),
                        admission_type=row.get("admission_type", None),
                        outcome=row.get("outcome", None),
                        stay_days=int(row["stay_days"]) if not pd.isna(row.get("stay_days")) else None,
                        treatment_cost=float(row["treatment_cost"]) if not pd.isna(row.get("treatment_cost")) else None,
                        insurance_type=row.get("insurance_type", None)
                    ))
                session.bulk_save_objects(records)
                session.commit()
                pct = min(100, (start + BATCH_SIZE) / total_rows * 100)
                print(f"  {min(start + BATCH_SIZE, total_rows):,}/{total_rows:,} ({pct:.0f}%)")
            print(f"[SUCCESS] Seeded patient_admissions table: {total_rows:,} rows inserted.")
        else:
            print(f"[WARNING] Patient admissions raw data not found at {admissions_csv}, skipping.")

        print("Database seeding phase complete!")
        
    except Exception as e:
        session.rollback()
        print(f"[ERROR] Database seeding failed: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    seed_db()
