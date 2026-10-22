import sqlite3, random, math, os
from datetime import datetime, timezone

random.seed(42)

DB = os.path.join(os.path.dirname(__file__), "hospitaliq.db")
conn = sqlite3.connect(DB)
c = conn.cursor()

WARD_TYPES = ['ICU', 'General', 'Maternity', 'Emergency']
YEARS = list(range(2017, 2025))
MONTHS = list(range(1, 13))

# Get all distinct hospitals with their score as proxy for size/quality
hospitals = c.execute("""
    SELECT h.hospital_name, h.state, h.district,
           COALESCE(AVG(h.hospital_score), 0.5) as score,
           COALESCE(MAX(h.hospital_type), '') as hosp_type
    FROM hospital_outcomes h
    GROUP BY h.hospital_name
""").fetchall()

print(f"Found {len(hospitals)} hospitals")

# Clear existing bed data
c.execute("DELETE FROM hospital_beds")
conn.commit()

# Seasonal occupancy adjustment per month (winter higher, summer lower)
SEASONAL_FACTOR = {
    1: 1.12, 2: 1.10, 3: 1.05, 4: 0.98, 5: 0.92, 6: 0.88,
    7: 0.90, 8: 0.95, 9: 0.98, 10: 1.02, 11: 1.08, 12: 1.15,
}

# COVID months: extreme surge Mar-Jun 2020, elevated 2021
COVID_SURGE = {(2020, 3): 1.8, (2020, 4): 2.0, (2020, 5): 1.9, (2020, 6): 1.7,
               (2020, 7): 1.5, (2020, 8): 1.4, (2020, 9): 1.3, (2020, 10): 1.2,
               (2020, 11): 1.2, (2020, 12): 1.3,
               (2021, 1): 1.3, (2021, 2): 1.2, (2021, 3): 1.3, (2021, 4): 1.6,
               (2021, 5): 1.7, (2021, 6): 1.4, (2021, 7): 1.2, (2021, 8): 1.1}

# Base occupancy floor by ward type
WARD_BASE_OCC = {'ICU': 0.55, 'General': 0.60, 'Maternity': 0.50, 'Emergency': 0.45}

# Ward fraction by hospital type
HOSP_WARD_FRAC = {
    'Tier1': {'ICU': 0.18, 'General': 0.45, 'Maternity': 0.15, 'Emergency': 0.22},
    'Tier2': {'ICU': 0.14, 'General': 0.50, 'Maternity': 0.18, 'Emergency': 0.18},
    'Tier3': {'ICU': 0.10, 'General': 0.55, 'Maternity': 0.20, 'Emergency': 0.15},
}

def get_tier(score, hosp_type):
    s = score or 0.5
    if s > 0.6 or 'Trust' in (hosp_type or ''):
        return 'Tier1'
    if s > 0.48:
        return 'Tier2'
    return 'Tier3'

def hospital_total_beds(score, state, district):
    base = 40 + int((score or 0.5) * 350)
    if any(m in str(district) for m in ['Central', 'City', 'Urban', 'North', 'South']):
        base = int(base * 1.4)
    if any(r in str(district) for r in ['Rural', 'gram', 'palli']):
        base = int(base * 0.65)
    return max(20, min(600, base + random.randint(-25, 25)))

total = 0
now_iso = datetime.now(timezone.utc).isoformat()

for name, state, district, score, hosp_type in hospitals:
    tier = get_tier(score, hosp_type)
    fracs = HOSP_WARD_FRAC[tier]
    tot = hospital_total_beds(score, state, district)

    # Hospital-specific baseline occupancy offset
    hosp_occ_offset = random.uniform(-0.08, 0.08)

    # Pre-compute base beds per ward for this hospital
    base_beds = {}
    for ward in WARD_TYPES:
        base_beds[ward] = max(2, int(tot * fracs[ward]))

    for year in YEARS:
        for month in MONTHS:
            seasonal = SEASONAL_FACTOR[month]
            covid = COVID_SURGE.get((year, month), 1.0)

            for ward in WARD_TYPES:
                # Bed count with natural monthly drift (±1-2 beds)
                drift = random.choice([-2, -1, 0, 0, 1, 2])
                beds = max(2, base_beds[ward] + drift)

                # Base occupancy: seasonal + hospital offset + random noise
                occ = WARD_BASE_OCC[ward] * seasonal * covid + hosp_occ_offset
                occ += random.uniform(-0.04, 0.04)
                occ = max(0.30, min(0.98, occ))
                occ_pct = round(occ * 100, 1)

                available = max(0, int(beds * (1 - occ)))

                c.execute("""
                    INSERT INTO hospital_beds
                    (state, district, hospital_name, ward_type, total_beds, available_beds, occupancy_rate, recorded_month, recorded_year, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (state, district, name, ward, beds, available, occ_pct, month, year, now_iso))
                total += 1

                if total % 30000 == 0:
                    conn.commit()

conn.commit()
print(f"\nDone! {total:,} bed records inserted")
print(f"Tier1: {sum(1 for h in hospitals if get_tier(h[3], h[4])=='Tier1')}, "
      f"Tier2: {sum(1 for h in hospitals if get_tier(h[3], h[4])=='Tier2')}, "
      f"Tier3: {sum(1 for h in hospitals if get_tier(h[3], h[4])=='Tier3')}")
