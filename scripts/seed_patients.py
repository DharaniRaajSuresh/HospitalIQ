import sqlite3, random, os
from datetime import datetime, timedelta, timezone

random.seed(42)

DB = os.path.join(os.path.dirname(__file__), "ml_pipeline", "data", "hospitaliq.db")
conn = sqlite3.connect(DB)
c = conn.cursor()

DISEASES = ['Cardiac', 'Stroke', 'Diabetes', 'Respiratory', 'Infectious',
            'Maternal', 'Neonatal', 'Trauma', 'Cancer', 'Renal',
            'Gastrointestinal', 'Neurological', 'Orthopedic', 'Pediatric', 'Psychiatric']

# Age distribution per disease
AGE_BY_DISEASE = {
    'Cardiac': {'0-14': 0.02, '15-44': 0.25, '45-64': 0.45, '65+': 0.28},
    'Stroke':  {'0-14': 0.01, '15-44': 0.15, '45-64': 0.40, '65+': 0.44},
    'Diabetes':{'0-14': 0.03, '15-44': 0.30, '45-64': 0.42, '65+': 0.25},
    'Respiratory':{'0-14': 0.15, '15-44': 0.30, '45-64': 0.30, '65+': 0.25},
    'Infectious':{'0-14': 0.20, '15-44': 0.40, '45-64': 0.25, '65+': 0.15},
    'Maternal':{'0-14': 0.0, '15-44': 0.95, '45-64': 0.05, '65+': 0.0},
    'Neonatal':{'0-14': 1.0, '15-44': 0.0, '45-64': 0.0, '65+': 0.0},
    'Trauma':  {'0-14': 0.10, '15-44': 0.55, '45-64': 0.25, '65+': 0.10},
    'Cancer':  {'0-14': 0.03, '15-44': 0.20, '45-64': 0.40, '65+': 0.37},
    'Renal':   {'0-14': 0.05, '15-44': 0.25, '45-64': 0.40, '65+': 0.30},
    'Gastrointestinal':{'0-14': 0.15, '15-44': 0.40, '45-64': 0.30, '65+': 0.15},
    'Neurological':{'0-14': 0.08, '15-44': 0.35, '45-64': 0.35, '65+': 0.22},
    'Orthopedic':{'0-14': 0.05, '15-44': 0.30, '45-64': 0.35, '65+': 0.30},
    'Pediatric':{'0-14': 0.95, '15-44': 0.05, '45-64': 0.0, '65+': 0.0},
    'Psychiatric':{'0-14': 0.05, '15-44': 0.50, '45-64': 0.30, '65+': 0.15},
}

GENDER = ['M', 'F']
ADMISSION_TYPES = ['emergency', 'planned', 'emergency', 'planned', 'referral']
INSURANCE = ['Government', 'Private', None, None, 'Private', 'Government', 'Government']

# Outcome, stay_days by disease severity
OUTCOME_PROBS = {
    'Cardiac': 0.06, 'Stroke': 0.09, 'Diabetes': 0.015, 'Respiratory': 0.04,
    'Infectious': 0.03, 'Maternal': 0.01, 'Neonatal': 0.04, 'Trauma': 0.025,
    'Cancer': 0.12, 'Renal': 0.05, 'Gastrointestinal': 0.02, 'Neurological': 0.04,
    'Orthopedic': 0.01, 'Pediatric': 0.015, 'Psychiatric': 0.005,
}

STAY_MEAN = {
    'Cardiac': 7, 'Stroke': 10, 'Diabetes': 5, 'Respiratory': 6,
    'Infectious': 5, 'Maternal': 4, 'Neonatal': 8, 'Trauma': 6,
    'Cancer': 12, 'Renal': 8, 'Gastrointestinal': 4, 'Neurological': 7,
    'Orthopedic': 5, 'Pediatric': 4, 'Psychiatric': 14,
}

# Seasonal admission multiplier per month
SEASONAL_ADMIT = {
    1: 1.15, 2: 1.10, 3: 1.05, 4: 0.95, 5: 0.90, 6: 0.85,
    7: 0.88, 8: 0.92, 9: 0.95, 10: 1.00, 11: 1.08, 12: 1.12,
}

# COVID surge for respiratory/infectious
COVID_MONTHS = {(2020,3),(2020,4),(2020,5),(2020,6),(2020,7),(2020,8),
                (2020,9),(2020,10),(2020,11),(2020,12),
                (2021,1),(2021,2),(2021,3),(2021,4),(2021,5),(2021,6)}

# Get all hospitals
hospitals = c.execute('''
    SELECT DISTINCT h.hospital_name, h.state, h.district,
           COALESCE(h.hospital_id, 'HOSP_' || substr(h.hospital_name,1,4) || substr(h.state,1,3))
    FROM hospital_outcomes h
    GROUP BY h.hospital_name
''').fetchall()
print(f'Hospitals: {len(hospitals)}')

# Disease weights for sampling
DISEASE_WT = {
    'Cardiac': 15, 'Stroke': 8, 'Diabetes': 12, 'Respiratory': 18,
    'Infectious': 12, 'Maternal': 8, 'Neonatal': 5, 'Trauma': 10,
    'Cancer': 5, 'Renal': 4, 'Gastrointestinal': 8, 'Neurological': 5,
    'Orthopedic': 6, 'Pediatric': 4, 'Psychiatric': 2,
}
disease_pool = []
for d, w in DISEASE_WT.items():
    disease_pool.extend([d] * w)

def pick_age(disease):
    dist = AGE_BY_DISEASE[disease]
    r = random.random()
    cum = 0
    for age, prob in dist.items():
        cum += prob
        if r <= cum:
            return age
    return '15-44'

def gen_admission_date(year, month):
    day = random.randint(1, 28)
    return datetime(year, month, day)

def gen_discharge(admit, stay):
    return admit + timedelta(days=stay)

# Clear existing
c.execute("DELETE FROM patient_admissions")
conn.commit()

now_iso = datetime.now(timezone.utc).isoformat()
total = 0
TARGET = 40000
YEARS = [2020, 2021, 2022, 2023, 2024]

for _ in range(TARGET):
    # Pick hospital
    h_name, h_state, h_district, h_id = random.choice(hospitals)

    # Pick date
    year = random.choice(YEARS)
    month = random.randint(1, 12)
    admit = gen_admission_date(year, month)
    days_off = random.randint(-2, 2)

    # Disease with seasonal + COVID boost
    disease = random.choice(disease_pool)
    if (year, month) in COVID_MONTHS and disease in ('Respiratory', 'Infectious'):
        if random.random() < 0.4:
            disease = random.choice(['Respiratory', 'Respiratory', 'Infectious'])

    age = pick_age(disease)
    gender = random.choice(GENDER)
    if disease == 'Maternal':
        gender = 'F'

    # Generate realistic stay_days with noise
    mean_stay = STAY_MEAN[disease]
    stay = max(1, int(random.gauss(mean_stay, mean_stay * 0.4) + 0.5))
    discharge = gen_discharge(admit, stay)

    # Outcome
    death_prob = OUTCOME_PROBS[disease]
    if age == '65+':
        death_prob *= 1.5
    if disease == 'Respiratory' and (year, month) in COVID_MONTHS:
        death_prob *= 2.0
    outcome = 'deceased' if random.random() < death_prob else 'recovered'

    # Treatment cost with disease/age variation
    base_cost = random.randint(50000, 500000)
    if disease in ('Cardiac', 'Cancer', 'Stroke'):
        base_cost = int(base_cost * 1.5)
    if age == '65+':
        base_cost = int(base_cost * 1.2)
    cost = int(base_cost * random.uniform(0.7, 1.3))

    admit_type = random.choice(ADMISSION_TYPES)
    insurance = random.choice(INSURANCE)
    pid = f'PAT_{total+1:06d}'

    c.execute("""
        INSERT INTO patient_admissions
        (patient_id, admission_date, discharge_date, hospital_id, hospital_name, state,
         disease, age_group, gender, admission_type, outcome, stay_days, treatment_cost, insurance_type, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (pid, admit.date().isoformat(), discharge.date().isoformat(),
          h_id, h_name, h_state, disease, age, gender,
          admit_type, outcome, stay, cost, insurance, now_iso))
    total += 1

    if total % 10000 == 0:
        conn.commit()
        print(f'  {total} records...')

conn.commit()
print(f'\nDone! {total:,} patient admission records')

# Stats
c2 = conn.cursor()
print(f'\nDisease distribution:')
for d, cnt in c2.execute('SELECT disease, COUNT(*) FROM patient_admissions GROUP BY disease ORDER BY cnt DESC').fetchall():
    print(f'  {d}: {cnt}')
print(f'\nOutcome: {c2.execute("SELECT outcome, COUNT(*) FROM patient_admissions GROUP BY outcome").fetchall()}')
print(f'Age: {c2.execute("SELECT age_group, COUNT(*) FROM patient_admissions GROUP BY age_group").fetchall()}')
print(f'Avg stay: {c2.execute("SELECT AVG(stay_days) FROM patient_admissions").fetchone()[0]:.1f} days')
print(f'Avg cost: Rs.{c2.execute("SELECT AVG(treatment_cost) FROM patient_admissions").fetchone()[0]:,.0f}')
