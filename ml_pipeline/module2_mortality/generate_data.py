import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml_pipeline"))

from districts import STATE_DISTRICTS

np.random.seed(42)

AGE_ANNUAL_RATES = {
    "0-14": 150,
    "15-44": 250,
    "45-64": 750,
    "65+": 6500,
}

CAUSE_DIST_BY_AGE = {
    "0-14": {
        "Neonatal": 0.60, "Infectious": 0.30, "Accident": 0.05,
        "Respiratory": 0.02, "Cardiac": 0.02, "Cancer": 0.005, "Maternal": 0.005,
    },
    "15-44": {
        "Accident": 0.45, "Cardiac": 0.20, "Infectious": 0.15,
        "Maternal": 0.08, "Cancer": 0.05, "Respiratory": 0.05, "Neonatal": 0.02,
    },
    "45-64": {
        "Cardiac": 0.40, "Cancer": 0.20, "Respiratory": 0.15,
        "Accident": 0.10, "Infectious": 0.10, "Maternal": 0.03, "Neonatal": 0.02,
    },
    "65+": {
        "Cardiac": 0.45, "Respiratory": 0.30, "Cancer": 0.15,
        "Accident": 0.04, "Infectious": 0.03, "Maternal": 0.02, "Neonatal": 0.01,
    },
}

CAUSE_SEVERITY = {
    "Cardiac": 1.8, "Cancer": 1.6, "Accident": 1.3,
    "Respiratory": 1.2, "Neonatal": 1.2, "Infectious": 1.0, "Maternal": 0.9,
}

STATE_HEALTHCARE = {
    "Kerala": 0.65, "Tamil Nadu": 0.70, "Delhi": 0.75, "Karnataka": 0.78,
    "Maharashtra": 0.80, "Telangana": 0.80, "Himachal Pradesh": 0.80,
    "Punjab": 0.82, "Andhra Pradesh": 0.85, "Uttarakhand": 0.85,
    "Gujarat": 0.85, "Haryana": 0.88, "Sikkim": 0.85,
    "West Bengal": 0.88, "Jammu and Kashmir": 0.90, "Odisha": 0.92,
    "Rajasthan": 0.95, "Assam": 0.98, "Mizoram": 0.95,
    "Tripura": 0.98, "Manipur": 1.00, "Jharkhand": 1.05,
    "Madhya Pradesh": 1.05, "Nagaland": 1.02,
    "Chhattisgarh": 1.08, "Meghalaya": 1.08,
    "Arunachal Pradesh": 1.10, "Bihar": 1.12, "Uttar Pradesh": 1.15,
    "Goa": 0.78,
}

URBAN_CAUSE_MULT = {
    "Cardiac": 1.3, "Cancer": 1.2, "Respiratory": 0.8,
    "Infectious": 0.7, "Accident": 0.9, "Maternal": 0.8, "Neonatal": 0.9,
}
RURAL_CAUSE_MULT = {
    "Cardiac": 0.7, "Cancer": 0.8, "Respiratory": 1.4,
    "Infectious": 1.4, "Accident": 1.1, "Maternal": 1.3, "Neonatal": 1.1,
}

MONTHLY_SEASONALITY = {
    "Cardiac":     [1.15, 0.97, 0.97, 0.97, 0.97, 0.97, 0.97, 0.97, 0.97, 0.97, 0.97, 1.15],
    "Respiratory": [1.45, 1.45, 0.775, 0.775, 0.775, 0.775, 0.775, 0.775, 0.775, 0.775, 1.45, 1.45],
    "Infectious":  [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 1.60, 1.60, 1.60, 0.80, 0.80, 0.80],
    "Cancer":      [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "Accident":    [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "Maternal":    [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.10, 1.10, 1.10, 1.00, 1.00, 1.00],
    "Neonatal":    [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
}

NORTH_INDIA_RESPIRATORY_BOOST = {
    "Delhi", "Uttar Pradesh", "Bihar", "Haryana", "Punjab", "Rajasthan",
}

COVID_MULTIPLIERS = {}
for m in range(3, 7):
    COVID_MULTIPLIERS[(2020, m)] = 1.8
for m in range(4, 7):
    COVID_MULTIPLIERS[(2021, m)] = 1.5
COVID_CAUSES = {"Respiratory", "Infectious"}
COVID_2021_RESPIRATORY_ONLY = True

STATE_POP_MILLIONS = {
    "Uttar Pradesh": 241.1, "Maharashtra": 127.5, "Bihar": 128.6,
    "West Bengal": 99.6, "Madhya Pradesh": 87.6, "Rajasthan": 81.9,
    "Tamil Nadu": 77.1, "Gujarat": 72.4, "Karnataka": 68.1,
    "Andhra Pradesh": 53.3, "Odisha": 46.6, "Telangana": 38.3,
    "Jharkhand": 39.9, "Assam": 36.5, "Kerala": 35.9,
    "Punjab": 30.9, "Haryana": 30.6, "Chhattisgarh": 30.2,
    "Delhi": 22.3, "Jammu and Kashmir": 13.6, "Uttarakhand": 11.9,
    "Himachal Pradesh": 7.5, "Tripura": 4.1, "Meghalaya": 3.4,
    "Manipur": 3.3, "Nagaland": 2.2, "Goa": 1.6,
    "Arunachal Pradesh": 1.6, "Mizoram": 1.2, "Sikkim": 0.7,
}

STATES = sorted(STATE_DISTRICTS.keys())
AGE_GROUPS = ["0-14", "15-44", "45-64", "65+"]
CAUSES = ["Cardiac", "Respiratory", "Infectious", "Cancer", "Accident", "Maternal", "Neonatal"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def assign_risk_cluster(death_rate):
    # Keep in sync with backend/predictors/risk_utils.py
    if death_rate > 150:
        return "Critical"
    elif death_rate > 100:
        return "High Risk"
    elif death_rate > 60:
        return "Moderate"
    else:
        return "Low Risk"


def generate_mortality_data():
    records = []

    for state in STATES:
        healthcare_factor = STATE_HEALTHCARE.get(state, 1.0)
        state_districts = STATE_DISTRICTS.get(state, [state])
        total_state_pop = int(STATE_POP_MILLIONS.get(state, 10) * 1_000_000)
        n_districts = len(state_districts)
        is_north_india = state in NORTH_INDIA_RESPIRATORY_BOOST

        district_rng = np.random.RandomState(abs(hash(f"mortality_pop_{state}")) % (2**31))
        district_pop_weights = district_rng.lognormal(0, 0.3, n_districts)
        district_pop_weights = district_pop_weights / district_pop_weights.sum()

        for d, district in enumerate(state_districts):
            district_seed = abs(hash(f"mort_{state}_{district}")) % (2**31)
            d_rng = np.random.RandomState(district_seed)

            is_urban = bool(d % 3 == 0)
            district_health_index = d_rng.uniform(0.5, 1.8)
            pollution_factor = d_rng.uniform(0.8, 1.6) if is_urban else d_rng.uniform(1.0, 1.4)
            district_death_mult = district_health_index * pollution_factor

            population = max(200_000, int(total_state_pop * district_pop_weights[d]))

            for year in range(2015, 2025):
                for month in range(1, 13):
                    for age_group in AGE_GROUPS:
                        annual_rate = AGE_ANNUAL_RATES[age_group]
                        monthly_base = annual_rate / 12.0
                        cause_dist = CAUSE_DIST_BY_AGE[age_group]

                        for cause in CAUSES:
                            cause_share = cause_dist[cause]
                            if cause_share == 0.0:
                                continue

                            severity = CAUSE_SEVERITY[cause]
                            urban_mult = (URBAN_CAUSE_MULT.get(cause, 1.0) if is_urban
                                          else RURAL_CAUSE_MULT.get(cause, 1.0))

                            seasonal_mult = MONTHLY_SEASONALITY[cause][month - 1]
                            if cause == "Respiratory" and is_north_india:
                                seasonal_mult *= 1.4

                            covid_mult = 1.0
                            if cause in COVID_CAUSES:
                                cm = COVID_MULTIPLIERS.get((year, month), 1.0)
                                if year == 2021 and cause != "Respiratory" and COVID_2021_RESPIRATORY_ONLY:
                                    cm = 1.0
                                covid_mult = cm

                            death_rate = (monthly_base * cause_share * severity
                                          * healthcare_factor * district_death_mult
                                          * urban_mult * seasonal_mult * covid_mult)

                            noise_seed = abs(hash(f"{state}_{district}_{year}_{month}_{age_group}_{cause}")) % (2**31)
                            noise_rng = np.random.RandomState(noise_seed)
                            noise = noise_rng.normal(0, death_rate * 0.05)
                            death_rate += noise
                            death_rate = max(0.5, death_rate)

                            death_count = max(1, int((death_rate * population) / 100_000))

                            risk_cluster = assign_risk_cluster(death_rate)

                            records.append({
                                "state": state,
                                "district": district,
                                "year": year,
                                "month": month,
                                "month_name": MONTH_NAMES[month - 1],
                                "age_group": age_group,
                                "cause_of_death": cause,
                                "death_count": death_count,
                                "death_rate": round(death_rate, 2),
                                "population": population,
                                "is_urban": is_urban,
                                "risk_cluster": risk_cluster,
                            })

    df = pd.DataFrame(records)

    raw_dir = PROJECT_ROOT / "ml_pipeline" / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "mortality_raw.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {len(df):,} mortality records -> {output_path}")
    print("\nMean death_rate by age_group:")
    print(df.groupby("age_group")["death_rate"].mean().round(2).to_string())
    print("\nMean death_rate by cause:")
    print(df.groupby("cause_of_death")["death_rate"].mean().round(2).to_string())
    print("\nRisk cluster distribution:")
    print(df["risk_cluster"].value_counts().to_string())
    print(f"\nDeath rate range: {df['death_rate'].min():.2f} - {df['death_rate'].max():.2f}")

    return df


if __name__ == "__main__":
    generate_mortality_data()
