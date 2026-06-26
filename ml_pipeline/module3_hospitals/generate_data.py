import sys
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml_pipeline"))

from districts import STATE_DISTRICTS

np.random.seed(42)

HOSPITAL_TYPES = ["Govt", "Private", "Trust", "NGO"]
HOSPITAL_TYPE_PROBS = [0.30, 0.40, 0.18, 0.12]

DISEASES = [
    "Cardiac", "Diabetes", "Dengue", "Tuberculosis",
    "Pneumonia", "Cancer", "Stroke", "Hepatitis", "Malaria", "Typhoid",
]

ACCREDITATIONS = ["NABH", "JCI", "ISO", "None"]
ACCRED_PROBS = [0.08, 0.02, 0.20, 0.70]

AGE_GROUPS = ["0-14", "15-44", "45-64", "65+"]

ACCRED_BONUS = {"NABH": 0.03, "JCI": 0.05, "ISO": 0.02, "None": 0.00}

DISEASE_SEVERITY = {
    "Cancer": -0.15, "Stroke": -0.12, "Cardiac": -0.08,
    "Pneumonia": -0.05, "Dengue": -0.02, "Tuberculosis": -0.04,
    "Hepatitis": -0.02, "Typhoid": -0.01, "Malaria": 0.00, "Diabetes": 0.03,
}

DISEASE_COST_MULT = {
    "Cardiac": 1.5, "Cancer": 1.3, "Dengue": 2.0, "Diabetes": 1.2,
}

DISEASE_STAY = {
    "Cardiac": (5, 10), "Stroke": (7, 14), "Cancer": (10, 21),
    "Dengue": (3, 7), "Malaria": (3, 7), "Typhoid": (5, 10),
    "Tuberculosis": (14, 30), "Pneumonia": (5, 12), "Hepatitis": (7, 14),
    "Diabetes": (3, 7),
}

DISEASE_AGE_PROBS = {
    "Cardiac":       [0.01, 0.15, 0.45, 0.39],
    "Cancer":        [0.05, 0.15, 0.40, 0.40],
    "Stroke":        [0.02, 0.10, 0.40, 0.48],
    "Dengue":        [0.20, 0.45, 0.25, 0.10],
    "Malaria":       [0.15, 0.40, 0.30, 0.15],
    "Typhoid":       [0.20, 0.40, 0.30, 0.10],
    "Tuberculosis":  [0.05, 0.35, 0.35, 0.25],
    "Pneumonia":     [0.15, 0.20, 0.30, 0.35],
    "Hepatitis":     [0.10, 0.35, 0.35, 0.20],
    "Diabetes":      [0.02, 0.20, 0.45, 0.33],
}

OUTCOME_BY_DISEASE = {
    "Dengue":        [0.95, 0.02, 0.03],
    "Malaria":       [0.94, 0.02, 0.04],
    "Typhoid":       [0.93, 0.03, 0.04],
    "Diabetes":      [0.92, 0.04, 0.04],
    "Pneumonia":     [0.88, 0.07, 0.05],
    "Hepatitis":     [0.87, 0.07, 0.06],
    "Tuberculosis":  [0.85, 0.10, 0.05],
    "Cardiac":       [0.82, 0.12, 0.06],
    "Stroke":        [0.75, 0.18, 0.07],
    "Cancer":        [0.70, 0.20, 0.10],
}

TREATMENT_COST = {
    "Cancer":       (200000, 500000),
    "Cardiac":      (150000, 400000),
    "Stroke":       (100000, 350000),
    "Tuberculosis": (30000, 150000),
    "Pneumonia":    (25000, 100000),
    "Hepatitis":    (40000, 120000),
    "Dengue":       (15000, 50000),
    "Malaria":      (10000, 40000),
    "Typhoid":      (15000, 50000),
    "Diabetes":     (10000, 30000),
}

COST_MULTIPLIER = {"Govt": 0.6, "Private": 2.0, "Trust": 1.0, "NGO": 0.8}

INSURANCE_TYPES = ["Government", "Private", "None"]
INSURANCE_PROBS = [0.35, 0.25, 0.40]

REAL_HOSPITALS_PER_STATE = {
    "Tamil Nadu": 1800, "Maharashtra": 2100, "Delhi": 400, "Karnataka": 2200,
    "Kerala": 1200, "Rajasthan": 1600, "Gujarat": 1900, "Uttar Pradesh": 2800,
    "Telangana": 900, "Andhra Pradesh": 1000, "West Bengal": 1500,
    "Haryana": 600, "Punjab": 700, "Odisha": 900, "Jharkhand": 400,
    "Bihar": 800, "Madhya Pradesh": 1400, "Chhattisgarh": 500,
    "Assam": 700, "Jammu and Kashmir": 500, "Himachal Pradesh": 300,
    "Uttarakhand": 250, "Goa": 80, "Meghalaya": 100, "Manipur": 80,
    "Mizoram": 60, "Nagaland": 80, "Tripura": 80, "Sikkim": 30,
    "Arunachal Pradesh": 50,
}

MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def generate_hospital_outcomes():
    records = []
    hospital_id = 1

    for state in sorted(REAL_HOSPITALS_PER_STATE.keys()):
        n_hospitals = REAL_HOSPITALS_PER_STATE[state]
        state_districts = STATE_DISTRICTS.get(state, [state])
        hospitals_per_district = max(1, n_hospitals // len(state_districts))

        for district in state_districts:
            n_in_district = min(hospitals_per_district, 30)

            for h in range(n_in_district):
                hospital_name = f"{state} {district} Hospital {chr(65 + h)}"
                htype = np.random.choice(HOSPITAL_TYPES, p=HOSPITAL_TYPE_PROBS)

                total_beds = int(np.random.lognormal(4.5, 0.6))
                total_beds = max(20, min(800, total_beds))

                icu_beds = int(total_beds * np.random.uniform(0.05, 0.08))
                icu_beds = max(2, icu_beds)

                specialist_count = int(total_beds * np.random.uniform(0.03, 0.06))
                specialist_count = max(1, specialist_count)

                accred = np.random.choice(ACCREDITATIONS, p=ACCRED_PROBS)

                accred_bonus = ACCRED_BONUS[accred]
                specialist_bonus = min(0.05, specialist_count / total_beds * 1.25)

                type_bonus = {"Private": 0.02, "Trust": 0.01, "Govt": 0.00, "NGO": -0.01}[htype]

                diseases_subset = np.random.choice(DISEASES, 5, replace=False)

                for disease in diseases_subset:
                    severity_penalty = DISEASE_SEVERITY[disease]
                    stay_min, stay_max = DISEASE_STAY[disease]
                    avg_stay = round(np.random.uniform(stay_min, stay_max), 1)

                    occupancy = np.random.uniform(0.60, 0.90)
                    overcrowding_penalty = max(0, (occupancy * 100 - 85) * 0.005)

                    success_rate = (0.90 + specialist_bonus + severity_penalty
                                    - overcrowding_penalty + accred_bonus + type_bonus
                                    + np.random.normal(0, 0.015))
                    success_rate = np.clip(success_rate, 0.60, 0.97)

                    total_cases = np.random.randint(50, 800)
                    success_count = int(total_cases * success_rate)
                    failure_count = total_cases - success_count

                    accred_sc = {"NABH": 3, "JCI": 3, "ISO": 2, "None": 1}[accred]
                    hospital_score = (
                        (success_rate * 0.5)
                        + (1.0 / max(avg_stay, 1) * 0.3)
                        + (accred_sc / 5.0 * 0.2)
                    )
                    rating = round(min(hospital_score * 1.25, 5.0), 2)

                    records.append({
                        "hospital_id": f"HOSP_{hospital_id:04d}",
                        "hospital_name": hospital_name,
                        "state": state,
                        "district": district,
                        "hospital_type": htype,
                        "disease": disease,
                        "total_cases": total_cases,
                        "success_count": success_count,
                        "failure_count": failure_count,
                        "success_rate": round(success_rate, 4),
                        "avg_stay_days": avg_stay,
                        "total_beds": total_beds,
                        "icu_beds": icu_beds,
                        "specialist_count": specialist_count,
                        "accreditation": accred,
                        "hospital_score": round(hospital_score, 4),
                        "rating": rating,
                    })

                hospital_id += 1

    df = pd.DataFrame(records)
    raw_dir = PROJECT_ROOT / "ml_pipeline" / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "hospital_outcomes_raw.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} hospital outcome records -> {output_path}")
    return df


def generate_patient_admissions():
    states = sorted(REAL_HOSPITALS_PER_STATE.keys())
    total_hospitals = sum(REAL_HOSPITALS_PER_STATE.values())
    state_probs = [REAL_HOSPITALS_PER_STATE[s] / total_hospitals for s in states]

    records = []
    num_records = 80000

    start_date = datetime(2015, 1, 1)
    end_date = datetime(2024, 12, 31)
    total_days = (end_date - start_date).days

    for i in range(num_records):
        patient_id = f"PAT_{i + 1:06d}"

        day_offset = np.random.randint(0, total_days)
        admission_date = start_date + timedelta(days=int(day_offset))

        disease = np.random.choice(DISEASES)

        age_probs = DISEASE_AGE_PROBS[disease]
        age_group = np.random.choice(AGE_GROUPS, p=age_probs)

        gender = "M" if np.random.random() < 0.515 else "F"

        stay_min, stay_max = DISEASE_STAY[disease]
        stay_mean = (stay_min + stay_max) / 2
        stay_std = (stay_max - stay_min) / 3
        stay_days = max(1, int(np.random.normal(stay_mean, stay_std)))
        discharge_date = admission_date + timedelta(days=stay_days)

        probs = np.array(OUTCOME_BY_DISEASE[disease], dtype=float)

        if age_group == "65+":
            probs[1] *= 1.5
            probs[0] *= 0.95

        is_covid_period = (admission_date.year in (2020, 2021))
        if is_covid_period and disease in ("Pneumonia",):
            probs[1] *= 2.0

        probs = probs / probs.sum()
        outcome = np.random.choice(["recovered", "deceased", "transferred"], p=probs)

        state = np.random.choice(states, p=state_probs)
        state_districts = STATE_DISTRICTS.get(state, [state])
        district = np.random.choice(state_districts)
        hosp_id = f"HOSP_{np.random.randint(1, 1500):04d}"
        hospital_name = f"{state} {district} Hospital"

        if disease in ("Cardiac", "Stroke"):
            admission_type = np.random.choice(["emergency", "planned"], p=[0.80, 0.20])
        else:
            admission_type = np.random.choice(["emergency", "planned"], p=[0.55, 0.45])

        cost_lo, cost_hi = TREATMENT_COST[disease]
        h_type = np.random.choice(HOSPITAL_TYPES, p=HOSPITAL_TYPE_PROBS)
        multiplier = COST_MULTIPLIER[h_type]
        icu_mult = DISEASE_COST_MULT.get(disease, 1.3)
        multiplier *= np.random.uniform(1.0, icu_mult)
        treatment_cost = int(np.random.randint(cost_lo, cost_hi + 1) * multiplier)

        insurance_type = np.random.choice(INSURANCE_TYPES, p=INSURANCE_PROBS)

        records.append({
            "patient_id": patient_id,
            "admission_date": admission_date.date(),
            "discharge_date": discharge_date.date(),
            "hospital_id": hosp_id,
            "hospital_name": hospital_name,
            "state": state,
            "disease": disease,
            "age_group": age_group,
            "gender": gender,
            "admission_type": admission_type,
            "outcome": outcome,
            "stay_days": stay_days,
            "treatment_cost": treatment_cost,
            "insurance_type": insurance_type,
        })

    df = pd.DataFrame(records)
    raw_dir = PROJECT_ROOT / "ml_pipeline" / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "patient_admissions_raw.csv"
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} patient admission records -> {output_path}")
    return df


if __name__ == "__main__":
    generate_hospital_outcomes()
    generate_patient_admissions()
