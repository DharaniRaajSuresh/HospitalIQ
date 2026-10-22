import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "ml_pipeline"))

from districts import STATE_DISTRICTS

np.random.seed(42)

BEDS_PER_1000 = {
    "Kerala": 1.2, "Tamil Nadu": 1.1, "Delhi": 1.5, "Goa": 1.0,
    "Karnataka": 0.9, "Maharashtra": 0.8, "Telangana": 0.8,
    "Andhra Pradesh": 0.7, "Gujarat": 0.7, "Himachal Pradesh": 0.7,
    "Uttarakhand": 0.65, "Punjab": 0.65, "Haryana": 0.6,
    "West Bengal": 0.6, "Rajasthan": 0.5, "Odisha": 0.5,
    "Assam": 0.45, "Jammu and Kashmir": 0.45, "Chhattisgarh": 0.4,
    "Madhya Pradesh": 0.4, "Uttar Pradesh": 0.35, "Jharkhand": 0.35,
    "Bihar": 0.3, "Meghalaya": 0.4, "Manipur": 0.4,
    "Mizoram": 0.5, "Nagaland": 0.4, "Tripura": 0.4,
    "Sikkim": 0.6, "Arunachal Pradesh": 0.4,
}

STATE_POP_MILLIONS = {
    "Tamil Nadu": 77.1, "Maharashtra": 127.5, "Delhi": 22.3,
    "Karnataka": 68.1, "West Bengal": 99.6, "Rajasthan": 81.9,
    "Gujarat": 72.4, "Uttar Pradesh": 241.1, "Kerala": 35.9,
    "Telangana": 38.3, "Bihar": 128.6, "Madhya Pradesh": 87.6,
    "Andhra Pradesh": 53.3, "Odisha": 46.6, "Jharkhand": 39.9,
    "Haryana": 30.6, "Punjab": 30.9, "Himachal Pradesh": 7.5,
    "Uttarakhand": 11.9, "Goa": 1.6, "Chhattisgarh": 30.2,
    "Assam": 36.5, "Jammu and Kashmir": 13.6, "Meghalaya": 3.4,
    "Manipur": 3.3, "Mizoram": 1.2, "Nagaland": 2.2,
    "Tripura": 4.1, "Sikkim": 0.7, "Arunachal Pradesh": 1.6,
}

WARD_TYPES = ["ICU", "General", "Maternity", "Emergency"]

WARD_FRACTION = {
    "ICU": 0.06, "General": 0.55, "Maternity": 0.22, "Emergency": 0.17,
}

WARD_OCC_BASE = {
    "ICU": 0.75, "General": 0.65, "Maternity": 0.60, "Emergency": 0.55,
}

SEASONAL_MODIFIERS = {
    1:  {"ICU": 0.15, "General": 0.10, "Maternity": 0.0,  "Emergency": 0.0},
    2:  {"ICU": 0.15, "General": 0.10, "Maternity": 0.0,  "Emergency": 0.0},
    3:  {"ICU": 0.0,  "General": 0.0,  "Maternity": 0.0,  "Emergency": 0.0},
    4:  {"ICU": 0.0,  "General": 0.0,  "Maternity": 0.05, "Emergency": 0.0},
    5:  {"ICU": 0.0,  "General": 0.0,  "Maternity": 0.05, "Emergency": 0.0},
    6:  {"ICU": 0.0,  "General": 0.0,  "Maternity": 0.05, "Emergency": 0.0},
    7:  {"ICU": 0.0,  "General": 0.08, "Maternity": 0.0,  "Emergency": 0.05},
    8:  {"ICU": 0.0,  "General": 0.08, "Maternity": 0.0,  "Emergency": 0.05},
    9:  {"ICU": 0.0,  "General": 0.08, "Maternity": 0.0,  "Emergency": 0.05},
    10: {"ICU": 0.0,  "General": 0.0,  "Maternity": 0.0,  "Emergency": 0.0},
    11: {"ICU": 0.15, "General": 0.10, "Maternity": 0.0,  "Emergency": 0.0},
    12: {"ICU": 0.15, "General": 0.10, "Maternity": 0.0,  "Emergency": 0.0},
}

SOUTHERN_STATES = {"Kerala", "Tamil Nadu", "Karnataka", "Maharashtra", "Telangana", "Andhra Pradesh"}

LOW_DENSITY_STATES = {"Bihar", "Uttar Pradesh", "Jharkhand", "Madhya Pradesh", "Chhattisgarh"}


def generate_bed_data():
    records = []
    states = sorted(STATE_DISTRICTS.keys())

    for state in states:
        pop_millions = STATE_POP_MILLIONS.get(state, 10)
        bed_density = BEDS_PER_1000.get(state, 0.5)

        if state in SOUTHERN_STATES:
            bed_density *= np.random.uniform(2.0, 3.0)
        if state in LOW_DENSITY_STATES:
            bed_density *= np.random.uniform(0.7, 0.9)

        state_districts = STATE_DISTRICTS.get(state, [state])
        annual_growth = 0.025 if state in LOW_DENSITY_STATES else 0.015

        for district in state_districts:
            district_seed = abs(hash(f"beds_{state}_{district}")) % (2**31)
            rng = np.random.RandomState(district_seed)

            district_pop_share = rng.uniform(0.03, 0.12)
            district_pop = max(80000, int(pop_millions * 1e6 * district_pop_share))
            total_district_beds = max(100, int(bed_density * district_pop / 1000))

            mean_occ_offset = rng.normal(0, 0.03)

            for ward_type in WARD_TYPES:
                ward_fraction = WARD_FRACTION[ward_type]

                if ward_type == "ICU":
                    icu_pct = rng.uniform(0.05, 0.08)
                    ward_fraction = icu_pct

                base_beds = max(5, int(total_district_beds * ward_fraction))
                base_occupancy = WARD_OCC_BASE[ward_type]

                for month_offset in range(120):
                    year = 2015 + month_offset // 12
                    month = (month_offset % 12) + 1

                    years_elapsed = month_offset / 12.0
                    growth_factor = (1.0 + annual_growth) ** years_elapsed
                    current_beds = max(5, int(base_beds * growth_factor))

                    if ward_type == "ICU":
                        current_beds = max(2, int(current_beds))

                    is_covid = (year == 2020 and month >= 3) or (year == 2021 and month <= 6)

                    if is_covid:
                        if ward_type == "ICU":
                            occupancy = rng.uniform(0.90, 0.97)
                        elif ward_type == "General":
                            occupancy = rng.uniform(0.80, 0.90)
                        elif ward_type == "Maternity":
                            occupancy = base_occupancy + rng.uniform(0.05, 0.10)
                        else:
                            occupancy = base_occupancy + rng.uniform(0.08, 0.15)
                    else:
                        seasonal_mod = SEASONAL_MODIFIERS[month][ward_type]
                        noise = rng.normal(0, 0.015)
                        occupancy = base_occupancy + seasonal_mod + noise + mean_occ_offset

                    occupancy = float(np.clip(occupancy, 0.10, 0.98))
                    available_beds = max(0, int(current_beds * (1.0 - occupancy)))
                    occupancy_rate = round(occupancy * 100, 2)

                    records.append({
                        "state": state,
                        "district": district,
                        "hospital_name": f"{state} {district} Hospital A",
                        "ward_type": ward_type,
                        "total_beds": current_beds,
                        "available_beds": available_beds,
                        "occupancy_rate": occupancy_rate,
                        "recorded_month": month,
                        "recorded_year": year,
                    })

    df = pd.DataFrame(records)

    raw_dir = PROJECT_ROOT / "ml_pipeline" / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    output_path = raw_dir / "beds_raw.csv"
    df.to_csv(output_path, index=False)

    print(f"Generated {len(df):,} bed records -> {output_path}")
    print(f"States: {df['state'].nunique()}, Districts: {df['district'].nunique()}")
    print(f"Year range: {df['recorded_year'].min()}-{df['recorded_year'].max()}")
    print("\nOccupancy rate (%) by ward type:")
    print(df.groupby("ward_type")["occupancy_rate"].agg(["mean", "std", "min", "max"]).round(2).to_string())
    print("\nCOVID ICU occupancy (2020-2021):")
    covid_icu = df[(df["ward_type"] == "ICU") & (df["recorded_year"].isin([2020, 2021]))]
    if len(covid_icu) > 0:
        print(f"  mean={covid_icu['occupancy_rate'].mean():.1f}%, max={covid_icu['occupancy_rate'].max():.1f}%")

    return df


if __name__ == "__main__":
    generate_bed_data()
