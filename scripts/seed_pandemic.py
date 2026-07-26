import sqlite3, random, os, sys, math
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.config import settings
from backend.database import is_postgres_available

db_url = settings.database_url
if "postgresql" in db_url and not is_postgres_available(db_url):
    db_dir = str(PROJECT_ROOT / "ml_pipeline" / "data")
    os.makedirs(db_dir, exist_ok=True)
    db_url = f"sqlite:///{db_dir}/hospitaliq.db"

DB = db_url.replace("sqlite:///", "")
if not os.path.isabs(DB):
    DB = os.path.join(str(PROJECT_ROOT), DB)

sys.path.insert(0, str(PROJECT_ROOT / "ml_pipeline"))
from districts import STATE_DISTRICTS

random.seed(42)

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

TOTAL_POP = sum(STATE_POP_MILLIONS.values()) * 1_000_000

DISEASE_PARAMS = {
    "COVID-19": {"cfr": 0.025, "r0": 2.5, "dur": 30, "icu": 0.08, "hosp_pct": 0.15},
    "Ebola":    {"cfr": 0.50, "r0": 1.8, "dur": 30, "icu": 0.60, "hosp_pct": 0.60},
    "H1N1":     {"cfr": 0.01, "r0": 1.5, "dur": 30, "icu": 0.05, "hosp_pct": 0.08},
    "SARS":     {"cfr": 0.10, "r0": 3.0, "dur": 30, "icu": 0.25, "hosp_pct": 0.35},
    "Nipah":    {"cfr": 0.50, "r0": 1.8, "dur": 30, "icu": 0.50, "hosp_pct": 0.55},
    "Marburg":  {"cfr": 0.55, "r0": 1.7, "dur": 30, "icu": 0.55, "hosp_pct": 0.58},
}

DISEASE_YEAR_TREND = {
    "COVID-19": -0.15,
    "Ebola":     0.02,
    "H1N1":     -0.03,
    "SARS":     -0.08,
    "Nipah":     0.10,
    "Marburg":   0.12,
}

DISEASE_SEASONAL = {
    "COVID-19": [1.3, 1.2, 1.1, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.1, 1.3],
    "Ebola":    [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "H1N1":     [1.4, 1.3, 1.1, 0.8, 0.7, 0.6, 0.6, 0.7, 0.8, 1.0, 1.2, 1.4],
    "SARS":     [1.2, 1.1, 1.0, 0.9, 0.8, 0.7, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2],
    "Nipah":    [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "Marburg":  [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
}

WAVE1_CASES = {3: 500, 4: 5000, 5: 15000, 6: 30000, 7: 50000, 8: 75000, 9: 97000, 10: 80000, 11: 40000, 12: 25000}
WAVE2_CASES = {1: 12000, 2: 30000, 3: 80000, 4: 414000, 5: 300000, 6: 100000, 7: 40000}

CFR_BY_MONTH = {}
for ym, cfr in [
    ((2020, 3), 2.5), ((2020, 4), 2.3), ((2020, 5), 2.0), ((2020, 6), 1.8),
    ((2020, 7), 1.6), ((2020, 8), 1.5), ((2020, 9), 1.4), ((2020, 10), 1.3),
    ((2020, 11), 1.2), ((2020, 12), 1.1),
    ((2021, 1), 1.1), ((2021, 2), 1.0), ((2021, 3), 1.0), ((2021, 4), 1.0),
    ((2021, 5), 1.0), ((2021, 6), 1.0), ((2021, 7), 1.0),
]:
    CFR_BY_MONTH[ym] = cfr

R0_BY_MONTH = {}
for ym, r0_val in [
    ((2020, 3), 2.0), ((2020, 4), 1.8), ((2020, 5), 1.6), ((2020, 6), 1.4),
    ((2020, 7), 1.3), ((2020, 8), 1.2), ((2020, 9), 1.1), ((2020, 10), 1.0),
    ((2020, 11), 0.9), ((2020, 12), 0.9),
    ((2021, 1), 0.9), ((2021, 2), 1.0), ((2021, 3), 1.2), ((2021, 4), 1.8),
    ((2021, 5), 1.5), ((2021, 6), 1.2), ((2021, 7), 0.8),
]:
    R0_BY_MONTH[ym] = r0_val


def get_district_pop_fraction(state, district):
    state_pop = STATE_POP_MILLIONS.get(state, 10) * 1_000_000
    districts = STATE_DISTRICTS.get(state, [state])
    nd = len(districts)
    di = districts.index(district) if district in districts else 0
    rng = random.Random(f"pop_frac_{state}_{district}")
    weights = [rng.uniform(0.5, 1.5) for _ in range(nd)]
    total_w = sum(weights)
    return weights[di] / total_w


def generate_covid_real():
    records = []

    for state, districts in STATE_DISTRICTS.items():
        state_pop = STATE_POP_MILLIONS.get(state, 10) * 1_000_000
        state_share = state_pop / TOTAL_POP

        for district in districts:
            dist_frac = get_district_pop_fraction(state, district)
            dist_pop = int(state_pop * dist_frac)

            for year in [2020, 2021]:
                for month in range(1, 13):
                    if year == 2020 and month < 3:
                        continue
                    if year == 2020 and month > 12:
                        continue
                    if year == 2021 and month > 7:
                        continue

                    wave = WAVE1_CASES if year == 2020 else WAVE2_CASES

                    if month not in wave:
                        continue

                    daily_cases = wave[month]
                    monthly_cases = int(daily_cases * 30 * state_share * dist_frac * 10)

                    if monthly_cases < 1:
                        continue

                    monthly_cases = max(2, monthly_cases)

                    cfr_pct = CFR_BY_MONTH.get((year, month), 1.0)
                    cfr_frac = cfr_pct / 100.0
                    deaths = max(0, int(monthly_cases * cfr_frac * random.uniform(0.8, 1.2)))
                    deaths = min(deaths, monthly_cases)

                    recovered = max(0, int((monthly_cases - deaths) * random.uniform(0.85, 0.98)))
                    active = max(0, monthly_cases - deaths - recovered)

                    bed_demand = int(monthly_cases * 0.15 * random.uniform(0.8, 1.2))

                    is_peak = (year == 2021 and month == 4)
                    icu_pct = 0.12 if is_peak else random.uniform(0.05, 0.08)
                    icu_demand = int(monthly_cases * icu_pct * random.uniform(0.8, 1.2))

                    vent_pct = random.uniform(0.03, 0.05)
                    if is_peak:
                        vent_pct = random.uniform(0.04, 0.06)
                    vent_demand = int(monthly_cases * vent_pct)

                    r0_eff = R0_BY_MONTH.get((year, month), 1.0) * random.uniform(0.9, 1.1)

                    records.append((
                        "COVID-19", state, district, year, month,
                        monthly_cases, deaths, recovered, active,
                        bed_demand, icu_demand, vent_demand,
                        round(r0_eff, 2), round(cfr_pct, 2),
                    ))

    return records


def generate_other_diseases():
    records = []

    for disease, params in DISEASE_PARAMS.items():
        if disease == "COVID-19":
            continue

        base_r0 = params["r0"]
        cfr = params["cfr"]
        icu = params["icu"]
        hosp_pct = params["hosp_pct"]
        trend = DISEASE_YEAR_TREND.get(disease, 0.0)
        seasonal = DISEASE_SEASONAL.get(disease, [1.0] * 12)

        for state, districts in STATE_DISTRICTS.items():
            state_pop = STATE_POP_MILLIONS.get(state, 10) * 1_000_000
            state_seed = random.uniform(0.6, 1.5)

            for district in districts:
                dist_frac = get_district_pop_fraction(state, district)
                pop = int(state_pop * dist_frac)
                scale = max(0.1, pop / 10_000_000)
                district_seed = random.uniform(0.7, 1.3)

                for year in range(2020, 2031):
                    year_factor = (1.0 + trend) ** (year - 2020)

                    num_waves = random.randint(1, 2)
                    wave_positions = sorted([random.uniform(0.1, 0.9) for _ in range(num_waves)])
                    wave_heights = [random.uniform(0.5, 1.0) for _ in range(num_waves)]
                    base_intensity = 120 * scale * district_seed * state_seed

                    for month in range(1, 13):
                        t = month / 12
                        wave = 0.0
                        for pos, height in zip(wave_positions, wave_heights):
                            phase = (t - pos) / 0.08
                            wave += height * math.exp(-(phase ** 2) / 2)
                        wave = max(0.01, wave * 0.6 + 0.4)
                        noise = random.uniform(0.7, 1.3)
                        season = seasonal[month - 1]
                        rate = base_intensity * wave * noise * year_factor * season
                        rate = max(2, rate)
                        confirmed = max(0, int(pop * rate / 100_000))
                        if confirmed == 0:
                            continue

                        yr_improvement = 1.0 - 0.02 * (year - 2020)
                        cfr_effective = cfr * max(0.5, yr_improvement)
                        cfr_jitter = cfr_effective * random.uniform(0.75, 1.25)
                        cfr_jitter = min(0.95, max(0.001, cfr_jitter))
                        deaths = max(0, min(int(confirmed * cfr_jitter), confirmed))
                        recovered_est = max(0, int((confirmed - deaths) * random.uniform(0.75, 0.95)))
                        active = max(0, confirmed - deaths - recovered_est)

                        bed = int(confirmed * hosp_pct * random.uniform(0.7, 1.3))
                        icu_bed = int(confirmed * icu * random.uniform(0.7, 1.3))
                        vent = int(icu_bed * random.uniform(0.25, 0.65))

                        yr_t = (year - 2020) / 10.0
                        eff_r0 = base_r0 * (1 - yr_t * 0.2 + 0.1 * wave) * random.uniform(0.8, 1.2)
                        eff_r0 = max(0.3, min(5.0, eff_r0))

                        records.append((
                            disease, state, district, year, month,
                            confirmed, deaths, min(recovered_est, confirmed),
                            min(active, confirmed), bed, icu_bed, vent,
                            round(eff_r0, 2), round(min(cfr_jitter * 100, 95), 2),
                        ))

    return records


def main():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM pandemic_outbreak")
    conn.commit()
    print("Cleared existing pandemic records")

    total = 0

    print("\nGenerating COVID-19 real data (Mar 2020 - Jul 2021)...")
    covid_records = generate_covid_real()
    c.executemany("""INSERT INTO pandemic_outbreak
        (disease,state,district,year,month,confirmed_cases,deaths,recovered,
         active_cases,bed_demand,icu_demand,ventilator_demand,reproduction_rate,case_fatality_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", covid_records)
    conn.commit()
    print(f"  COVID-19: {len(covid_records)} records")
    total += len(covid_records)

    print("\nGenerating COVID-19 endemic tail (Aug 2021 - 2030)...")
    covid_synthetic = []
    for state, districts in STATE_DISTRICTS.items():
        state_pop = STATE_POP_MILLIONS.get(state, 10) * 1_000_000
        pop_scale = state_pop / 10_000_000
        rng = random.Random(f"covid_tail_{state}")

        for district in districts:
            dist_frac = get_district_pop_fraction(state, district)
            pop = int(state_pop * dist_frac)
            dist_seed = rng.uniform(0.7, 1.3)

            for year in range(2021, 2031):
                for month in range(1, 13):
                    if year == 2021 and month <= 7:
                        continue

                    # Endemic wave pattern: cases decline from 2021 peak to ~20% by 2030
                    # with seasonal winter spikes (Nov-Feb) and smaller summer waves
                    year_factor = max(0.02, (1.0 - 0.20) ** (year - 2021))
                    season = DISEASE_SEASONAL["COVID-19"][month - 1]

                    # Multi-wave annual pattern (2-3 waves per year, like real COVID endemic)
                    t = month / 12
                    wave1 = math.exp(-((t - 0.15) / 0.10) ** 2 / 2) * 1.0   # Feb-Mar
                    wave2 = math.exp(-((t - 0.45) / 0.12) ** 2 / 2) * 0.6   # Jun-Jul
                    wave3 = math.exp(-((t - 0.85) / 0.08) ** 2 / 2) * 0.8   # Nov-Dec
                    wave_boost = max(0.3, wave1 + wave2 + wave3)

                    noise = rng.uniform(0.5, 1.5)
                    rate = 20 * pop_scale * dist_seed * year_factor * season * wave_boost * noise
                    confirmed = max(0, int(pop * rate / 100_000))
                    if confirmed < 2:
                        continue

                    cfr_eff = max(0.001, 0.008 * (1.0 - 0.10 * (year - 2021)))
                    deaths = max(0, int(confirmed * cfr_eff * rng.uniform(0.7, 1.3)))
                    deaths = min(deaths, confirmed)
                    recovered = max(0, int((confirmed - deaths) * rng.uniform(0.85, 0.98)))
                    active = max(0, confirmed - deaths - recovered)

                    bed = int(confirmed * 0.15 * rng.uniform(0.7, 1.3))
                    icu_bed = int(confirmed * 0.05 * rng.uniform(0.7, 1.3))
                    vent = int(icu_bed * rng.uniform(0.25, 0.65))
                    r0_eff = rng.uniform(0.6, 1.2)

                    covid_synthetic.append((
                        "COVID-19", state, district, year, month,
                        confirmed, deaths, recovered, active,
                        bed, icu_bed, vent, round(r0_eff, 2), round(cfr_eff * 100, 2),
                    ))

    c.executemany("""INSERT INTO pandemic_outbreak
        (disease,state,district,year,month,confirmed_cases,deaths,recovered,
         active_cases,bed_demand,icu_demand,ventilator_demand,reproduction_rate,case_fatality_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", covid_synthetic)
    conn.commit()
    print(f"  COVID-19 synthetic: {len(covid_synthetic)} records")
    total += len(covid_synthetic)

    print("\nGenerating other diseases (2020-2030)...")
    other_records = generate_other_diseases()
    c.executemany("""INSERT INTO pandemic_outbreak
        (disease,state,district,year,month,confirmed_cases,deaths,recovered,
         active_cases,bed_demand,icu_demand,ventilator_demand,reproduction_rate,case_fatality_rate)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", other_records)
    conn.commit()
    total += len(other_records)

    disease_counts = {}
    for row in c.execute("SELECT disease, COUNT(*) FROM pandemic_outbreak GROUP BY disease ORDER BY disease"):
        disease_counts[row[0]] = row[1]

    print(f"\n{'='*60}")
    print(f"{'Disease':20s} {'Records':>10s}")
    print(f"{'='*60}")
    for d, cnt in sorted(disease_counts.items()):
        print(f"{d:20s} {cnt:>10,}")
    print(f"{'='*60}")
    print(f"{'TOTAL':20s} {total:>10,}")

    print(f"\n{'Year Distribution':^60}")
    print(f"{'='*60}")
    for row in c.execute("SELECT year, COUNT(*), SUM(confirmed_cases) FROM pandemic_outbreak GROUP BY year ORDER BY year"):
        yr, cnt, cases = row
        print(f"  {yr}: {cnt:>8,} records, {int(cases or 0):>12,} cases")

    conn.close()
    print(f"\nDone! {total} total pandemic records generated.")


if __name__ == "__main__":
    main()
