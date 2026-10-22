import sqlite3, random, os, sys, time
from datetime import datetime, date, timedelta
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

random.seed(42)
t_start = time.time()

conn = sqlite3.connect(DB)
c = conn.cursor()
BATCH = 10000

STATES_POP = [
    ("Uttar Pradesh", 0.20), ("Maharashtra", 0.10), ("Bihar", 0.09),
    ("West Bengal", 0.08), ("Madhya Pradesh", 0.07), ("Tamil Nadu", 0.06),
    ("Rajasthan", 0.06), ("Karnataka", 0.06), ("Gujarat", 0.05),
    ("Andhra Pradesh", 0.04), ("Odisha", 0.04), ("Telangana", 0.03),
    ("Kerala", 0.03), ("Jharkhand", 0.03), ("Assam", 0.03),
    ("Punjab", 0.03), ("Chhattisgarh", 0.03), ("Haryana", 0.02),
    ("Delhi", 0.02), ("Uttarakhand", 0.01),
]
STATE_NAMES = [s for s, _ in STATES_POP]
STATE_WEIGHTS = [w for _, w in STATES_POP]

DISTRICT_POOL = [
    "Central", "North", "South", "East", "West", "Rural",
    "Urban", "Hill", "Coastal", "Industrial", "Suburban", "Tribal",
]
URBAN_DISTRICTS = {"Urban", "Industrial", "Suburban"}

BLOOD_DIST = ["O+", "B+", "A+", "AB+", "O-", "B-", "A-", "AB-"]
BLOOD_WT   = [0.32, 0.32, 0.22, 0.08, 0.02, 0.02, 0.01, 0.01]

AGE_BUCKETS = [(0, 14, 0.25), (15, 44, 0.45), (45, 64, 0.20), (65, 95, 0.10)]


def random_age():
    r = random.random()
    cum = 0.0
    for lo, hi, wt in AGE_BUCKETS:
        cum += wt
        if r <= cum:
            return random.randint(lo, hi)
    return random.randint(65, 95)


def random_gender():
    return "Male" if random.random() < 0.515 else "Female"


def generate_conditions(age, gender, district_type):
    conditions = set()
    is_urban = district_type in URBAN_DISTRICTS

    obesity_rate = 0.06 * (2.0 if is_urban else 1.0)
    if random.random() < obesity_rate:
        conditions.add("Obesity")

    if age >= 30:
        base_ht = 0.18 + 0.005 * (age - 30)
        if gender == "Male":
            base_ht *= (24.0 / 22.0)
        else:
            base_ht *= (21.0 / 22.0)
        if "Obesity" in conditions:
            base_ht *= 2.0
        base_ht = min(base_ht, 0.85)
        if random.random() < base_ht:
            conditions.add("Hypertension")

    if age >= 25:
        base_dm = 0.08 + 0.003 * (age - 25)
        if gender == "Male":
            base_dm *= (15.0 / 14.0)
        else:
            base_dm *= (13.0 / 14.0)
        if is_urban:
            base_dm *= 2.0
        if "Obesity" in conditions:
            base_dm *= 2.0
        base_dm = min(base_dm, 0.75)
        if random.random() < base_dm:
            conditions.add("Diabetes")

    if age >= 45:
        base_cd = 0.04 + 0.002 * (age - 45)
        if gender == "Male":
            base_cd *= 1.75
        base_cd = min(base_cd, 0.50)
        if random.random() < base_cd:
            conditions.add("Cardiac")

    if age <= 14 or age >= 55:
        if random.random() < 0.04:
            conditions.add("Asthma")

    if age >= 20:
        thyroid_rate = 0.06 if gender == "Female" else 0.015
        if random.random() < thyroid_rate:
            conditions.add("Thyroid")

    renal_rate = 0.01
    if "Diabetes" in conditions:
        renal_rate = 0.10
    elif "Hypertension" in conditions:
        renal_rate = 0.04
    if random.random() < renal_rate:
        conditions.add("Renal")

    return conditions


FIRST_NAMES_M = [
    "Aarav","Vivaan","Aditya","Arjun","Rohit","Amit","Rahul","Vikram","Raj","Deepak",
    "Arun","Vijay","Kiran","Shyam","Ravi","Sanjay","Anil","Sunil","Prakash","Manoj",
    "Suresh","Dinesh","Ramesh","Ganesh","Mahesh","Vishal","Akhil","Nikhil","Harsh","Rohan",
    "Karan","Aryan","Yash","Shiv","Aman","Gaurav","Nitin","Sachin","Puneet","Tarun",
    "Ankur","Lalit","Hemant","Naveen","Jatin","Mohit","Amitabh","Rajat","Kunal","Abhishek",
    "Siddharth","Pranav","Tanmay","Chirag","Dhruv","Hitesh","Milan","Om","Parth","Varun",
    "Ajay","Bharat","Chandan","Devendra","Eknath","Farhan","Girish","Hari","Ishan","Jagdish",
    "Kamal","Laxman","Mohan","Narayan","Omprakash","Parvez","Qadir","Ratan","Satyam","Tushar",
    "Uday","Veerendra","Wasim","Yogesh","Zubin",
]
FIRST_NAMES_F = [
    "Priya","Sneha","Ananya","Diya","Riya","Neha","Kavya","Aanya","Nandini","Meera",
    "Sunita","Geeta","Lakshmi","Seema","Pooja","Shweta","Anita","Sarita","Rekha","Asha",
    "Kiran","Usha","Lata","Vimala","Padma","Sita","Radha","Ganga","Yamuna","Kaveri",
    "Shanti","Preeti","Nisha","Kajal","Naina","Isha","Tara","Maya","Aditi","Vani",
    "Bhavna","Chitra","Deepa","Esha","Farida","Gauri","Hema","Indira","Jaya","Kanti",
    "Lavanya","Madhu","Nalini","Pallavi","Rashmi","Sandhya","Tanvi","Uma","Vidya","Zara",
    "Aishwarya","Bhagya","Charvi","Damini","Ekta","Falguni","Gargi","Harshita","Ila","Jyoti",
    "Kalpana","Lipika","Mrunal","Nirali","Parul","Quasar","Ritu","Surbhi","Trupti","Vaishali",
]
LAST_NAMES = [
    "Sharma","Verma","Patel","Singh","Kumar","Reddy","Gupta","Joshi","Nair","Menon",
    "Das","Bose","Choudhury","Iyer","Rao","Deshmukh","Kulkarni","Pillai","Nayar","Mishra",
    "Tiwari","Pandey","Dubey","Agarwal","Mehta","Shah","Thakur","Yadav","Khan","Ansari",
    "Shaikh","Sultan","Begum","Dutta","Sen","Pal","Ghosh","Majumdar","Bhatt","Acharya",
    "Shetty","Hegde","Kamat","Naidu","Chowdhury","Banerjee","Mukherjee","Chatterjee","Sarkar","Bhowmick",
]

STREETS = [
    "MG Road", "Station Road", "Lake View", "Gandhi Nagar", "Park Street",
    "Sector 5", "Sector 12", "Civil Lines", "Bazaar Street", "Temple Road",
    "Ring Road", "NH Road", "Collector Road", "Market Road", "School Road",
]

HOSPITALS = [
    "AIIMS", "Fortis", "Apollo", "Max", "Medanta", "KIMS", "JIPMER", "PGI",
    "Narayana", "Manipal", "Safdarjung", "RML", "CMC Vellore", "NIMHANS",
]
HOSPITAL_CITIES = [
    "Delhi", "Mumbai", "Bangalore", "Chennai", "Hyderabad",
    "Pune", "Lucknow", "Kolkata", "Jaipur", "Ahmedabad",
]

VACCINE_SCHEDULE = {
    "Covishield": {
        "virus_name": "COVID-19",
        "share": 0.75,
        "doses": [2, 3],
        "dose_weights": [60, 40],
        "eff_range": (0.70, 0.80),
        "date_start": date(2021, 1, 16),
        "date_end": date(2023, 12, 31),
        "gap_days": 84,
    },
    "Covaxin": {
        "virus_name": "COVID-19",
        "share": 0.12,
        "doses": [2, 3],
        "dose_weights": [65, 35],
        "eff_range": (0.65, 0.78),
        "date_start": date(2021, 1, 16),
        "date_end": date(2023, 12, 31),
        "gap_days": 28,
    },
    "H1N1 Vaccine": {
        "virus_name": "H1N1",
        "share": 0.04,
        "doses": [1, 2],
        "dose_weights": [70, 30],
        "eff_range": (0.55, 0.65),
        "date_start": date(2019, 1, 1),
        "date_end": date(2023, 12, 31),
        "gap_days": 28,
    },
    "Hepatitis B Vaccine": {
        "virus_name": "Hepatitis B",
        "share": 0.04,
        "doses": [3],
        "dose_weights": [100],
        "eff_range": (0.80, 0.90),
        "date_start": date(2015, 1, 1),
        "date_end": date(2023, 12, 31),
        "gap_days": 30,
    },
    "Seasonal Flu Vaccine": {
        "virus_name": "Seasonal Flu",
        "share": 0.02,
        "doses": [1],
        "dose_weights": [100],
        "eff_range": (0.50, 0.60),
        "date_start": date(2020, 1, 1),
        "date_end": date(2023, 12, 31),
        "gap_days": 0,
    },
}

CITIES_IN = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow",
    "Surat", "Bhopal", "Patna", "Indore", "Nagpur",
    "Thiruvananthapuram", "Guwahati", "Bhubaneswar", "Chandigarh", "Ranchi",
]
CITIES_OUT = [
    "Dubai", "Bangkok", "Singapore", "London", "New York",
    "Toronto", "Sydney", "Kuala Lumpur", "Sharjah", "Riyadh",
    "Doha", "Muscat", "Colombo", "Kathmandu", "Dhaka",
]
PILGRIMAGE_CITIES = [
    "Varanasi", "Haridwar", "Rishikesh", "Tirupati", "Shirdi",
    "Amritsar", "Puri", "Dwarka", "Rameshwaram", "Kedarnath",
    "Bodh Gaya", "Ajmer", "Mathura", "Vrindavan", "Madurai",
]
TRAVEL_PURPOSES = ["Business", "Tourism", "Medical", "Education", "Family Visit", "Pilgrimage"]

FAMILY_COND = ["Diabetes", "Cardiac", "Cancer", "Hypertension", "Asthma", "Stroke", "Renal Disease", "Thyroid"]
FAMILY_REL = ["Father", "Mother", "Brother", "Sister", "Grandfather", "Grandmother", "Uncle", "Aunt"]

FAMILY_CORR = {
    "Cardiac": 0.60,
    "Diabetes": 0.50,
    "Hypertension": 0.40,
}

now_iso = datetime.now().isoformat()

for tbl in ["family_history", "travel_history", "vaccine_history", "patients", "virus_registry"]:
    c.execute(f"DELETE FROM {tbl}")
conn.commit()
print("[CLEAR] Deleted existing data from 5 tables")

VIRUSES = [
    ("COVID-19",  0.02, 2.5, 5,  "airborne", 1, 0.72, 1,
     "SARS-CoV-2. CFR 2% (WHO 2023). Higher risk for elderly and comorbid patients."),
    ("Ebola",     0.50, 1.8, 10, "contact",  1, 0.76, 0,
     "Filovirus. CFR 50% (WHO 2022). rVSV-ZEBOV vaccine 76% effective."),
    ("H1N1",      0.01, 1.5, 2,  "airborne", 1, 0.62, 1,
     "Influenza A/H1N1. CFR ~1% (CDC). Oseltamivir effective if given early."),
    ("Marburg",   0.50, 1.7, 7,  "contact",  0, 0.0,  0,
     "Filovirus. CFR ~50% (WHO). No approved vaccine or specific antiviral."),
    ("Nipah",     0.65, 0.5, 12, "contact",  0, 0.0,  1,
     "Henipavirus. CFR 40-75% (WHO). Fruit bat reservoir. Supportive care only."),
    ("SARS",      0.10, 3.0, 5,  "airborne", 0, 0.0,  1,
     "SARS-CoV-1. CFR ~10% (WHO 2003). Contained since 2004. No recurrence."),
]

c.executemany(
    """INSERT INTO virus_registry
       (virus_name, fatality_rate, reproductive_rate, incubation_period_days,
        transmission_mode, vaccine_available, vaccine_effectiveness,
        treatment_available, notes, created_at)
       VALUES (?,?,?,?,?,?,?,?,?,?)""",
    [(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8], now_iso) for v in VIRUSES],
)
conn.commit()
print(f"[OK] {len(VIRUSES)} viruses registered")

NUM_PATIENTS = 10000
print(f"Generating {NUM_PATIENTS:,} patients...")
t0 = time.time()

patient_meta = {}
patient_batch = []

for i in range(1, NUM_PATIENTS + 1):
    state = random.choices(STATE_NAMES, weights=STATE_WEIGHTS, k=1)[0]
    district_type = random.choice(DISTRICT_POOL)
    district = district_type + " " + state.split()[-1]

    age = random_age()
    gender = random_gender()

    try:
        dob = date.today().replace(year=date.today().year - age) - timedelta(days=random.randint(0, 365))
    except ValueError:
        dob = date.today() - timedelta(days=age * 365 + random.randint(0, 365))

    blood = random.choices(BLOOD_DIST, weights=BLOOD_WT, k=1)[0]

    first = random.choice(FIRST_NAMES_F) if gender == "Female" else random.choice(FIRST_NAMES_M)
    name = first + " " + random.choice(LAST_NAMES)

    contact = f"+91-{random.randint(7000000000, 9999999999)}"
    address = f"{random.randint(1,999)}, {random.choice(STREETS)}, {district}, {state}"

    conds = generate_conditions(age, gender, district_type)
    cond_str = ", ".join(sorted(conds))

    patient_meta[i] = (age, gender, conds, district_type)

    patient_batch.append((
        name, dob.isoformat(), age, blood, gender, contact,
        address, state, district, cond_str, now_iso,
    ))

    if len(patient_batch) >= BATCH:
        c.executemany(
            """INSERT INTO patients
               (patient_name, dob, age, blood_group, gender, contact,
                address, state, district, pre_existing_conditions, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            patient_batch,
        )
        conn.commit()
        patient_batch = []
        print(f"  {i:,} patients... ({time.time()-t0:.1f}s)")

if patient_batch:
    c.executemany(
        """INSERT INTO patients
           (patient_name, dob, age, blood_group, gender, contact,
            address, state, district, pre_existing_conditions, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        patient_batch,
    )
    conn.commit()
print(f"[OK] {NUM_PATIENTS:,} patients created ({time.time()-t0:.1f}s)")

print("Generating vaccine records...")
t0 = time.time()
vaccine_batch = []
v_total = 0

for pid in range(1, NUM_PATIENTS + 1):
    for vname, vsched in VACCINE_SCHEDULE.items():
        if random.random() < vsched["share"]:
            num_doses = random.choices(vsched["doses"], weights=vsched["dose_weights"], k=1)[0]

            range_days = (vsched["date_end"] - vsched["date_start"]).days
            first_dose_offset = random.randint(0, max(0, range_days - num_doses * vsched["gap_days"]))
            first_dose_date = vsched["date_start"] + timedelta(days=first_dose_offset)

            for dose in range(1, num_doses + 1):
                vdate = first_dose_date + timedelta(days=(dose - 1) * vsched["gap_days"])
                if vdate > vsched["date_end"]:
                    vdate = vsched["date_end"]

                hospital = f"{random.choice(HOSPITALS)} {random.choice(HOSPITAL_CITIES)}"
                eff = round(random.uniform(*vsched["eff_range"]), 2)
                batch_num = f"BATCH-{random.randint(1000, 9999)}"

                vaccine_batch.append((
                    pid, vname, dose, vdate.isoformat(), hospital,
                    batch_num, vsched["virus_name"], eff, now_iso,
                ))
                v_total += 1

    if len(vaccine_batch) >= BATCH:
        c.executemany(
            """INSERT INTO vaccine_history
               (patient_id, vaccine_name, dose_number, vaccination_date,
                hospital_name, batch_number, virus_name, effectiveness, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            vaccine_batch,
        )
        conn.commit()
        vaccine_batch = []
        if v_total % 10000 == 0:
            print(f"  {v_total:,} vaccines... ({time.time()-t0:.1f}s)")

if vaccine_batch:
    c.executemany(
        """INSERT INTO vaccine_history
           (patient_id, vaccine_name, dose_number, vaccination_date,
            hospital_name, batch_number, virus_name, effectiveness, created_at)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        vaccine_batch,
    )
    conn.commit()
print(f"[OK] {v_total:,} vaccine records ({time.time()-t0:.1f}s)")

print("Generating travel records...")
t0 = time.time()
travel_batch = []
trav_total = 0

for pid in range(1, NUM_PATIENTS + 1):
    age, gender, conds, _ = patient_meta[pid]

    if random.random() < 0.35:
        num_trips = random.choices([1, 2, 3, 4], weights=[45, 30, 15, 10])[0]
        for _ in range(num_trips):
            if age >= 55 and random.random() < 0.35:
                purpose = "Pilgrimage"
            elif 25 <= age <= 55 and random.random() < 0.30:
                purpose = "Business"
            elif 18 <= age <= 30 and random.random() < 0.25:
                purpose = "Education"
            else:
                purpose = random.choice(TRAVEL_PURPOSES)

            from_loc = random.choice(CITIES_IN)
            if purpose == "Pilgrimage":
                to_loc = random.choice(PILGRIMAGE_CITIES)
            elif purpose in ("Business", "Tourism") and 25 <= age <= 55 and random.random() < 0.30:
                to_loc = random.choice(CITIES_OUT)
            elif purpose == "Medical":
                to_loc = random.choice(["Delhi", "Mumbai", "Bangalore", "Chennai", "Vellore", "Hyderabad"])
            else:
                to_loc = random.choice([c for c in CITIES_IN if c != from_loc])

            days_ago = random.randint(30, 800)
            start = date.today() - timedelta(days=days_ago)
            duration = random.randint(2, 21)
            end = start + timedelta(days=duration)

            travel_batch.append((
                pid, from_loc, to_loc, start.isoformat(), end.isoformat(), purpose, now_iso,
            ))
            trav_total += 1

    if len(travel_batch) >= BATCH:
        c.executemany(
            """INSERT INTO travel_history
               (patient_id, from_location, to_location, travel_date,
                return_date, purpose, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            travel_batch,
        )
        conn.commit()
        travel_batch = []

if travel_batch:
    c.executemany(
        """INSERT INTO travel_history
           (patient_id, from_location, to_location, travel_date,
            return_date, purpose, created_at)
           VALUES (?,?,?,?,?,?,?)""",
        travel_batch,
    )
    conn.commit()
print(f"[OK] {trav_total:,} travel records ({time.time()-t0:.1f}s)")

print("Generating family history records...")
t0 = time.time()
fam_batch = []
fam_total = 0

for pid in range(1, NUM_PATIENTS + 1):
    _, _, conds, _ = patient_meta[pid]

    if random.random() < 0.35:
        num_fam = random.choices([1, 2, 3], weights=[50, 35, 15])[0]

        for _ in range(num_fam):
            rel = random.choice(FAMILY_REL)

            fam_cond = None
            for patient_cond, corr_prob in FAMILY_CORR.items():
                if patient_cond in conds and random.random() < corr_prob:
                    fam_cond = patient_cond
                    break

            if fam_cond is None:
                fam_cond = random.choice(FAMILY_COND)

            if fam_cond in ("Diabetes", "Hypertension"):
                diag_age = random.randint(30, 70)
            elif fam_cond in ("Cardiac", "Stroke"):
                diag_age = random.randint(40, 75)
            elif fam_cond == "Cancer":
                diag_age = random.randint(35, 80)
            elif fam_cond == "Asthma":
                diag_age = random.randint(5, 60)
            elif fam_cond == "Thyroid":
                diag_age = random.randint(20, 55)
            elif fam_cond == "Renal Disease":
                diag_age = random.randint(40, 70)
            else:
                diag_age = random.randint(25, 75)

            deceased_base = 0.25
            if fam_cond in ("Cardiac", "Cancer", "Stroke"):
                deceased_base = 0.40
            if rel in ("Grandfather", "Grandmother"):
                deceased_base += 0.20
            deceased = random.random() < deceased_base

            fam_batch.append((pid, rel, fam_cond, diag_age, deceased, now_iso))
            fam_total += 1

    if len(fam_batch) >= BATCH:
        c.executemany(
            """INSERT INTO family_history
               (patient_id, relationship, condition, age_at_diagnosis,
                is_deceased, created_at)
               VALUES (?,?,?,?,?,?)""",
            fam_batch,
        )
        conn.commit()
        fam_batch = []

if fam_batch:
    c.executemany(
        """INSERT INTO family_history
           (patient_id, relationship, condition, age_at_diagnosis,
            is_deceased, created_at)
           VALUES (?,?,?,?,?,?)""",
        fam_batch,
    )
    conn.commit()
print(f"[OK] {fam_total:,} family history records ({time.time()-t0:.1f}s)")

t_elapsed = time.time() - t_start
print(f"\n{'='*50}")
print(f"  SEED COMPLETE in {t_elapsed:.1f}s")
print(f"{'='*50}")
print(f"  Patients:        {NUM_PATIENTS:,}")
print(f"  Vaccines:        {v_total:,}")
print(f"  Travel:          {trav_total:,}")
print(f"  Family:          {fam_total:,}")
print(f"{'='*50}")
for tbl in ["virus_registry", "patients", "vaccine_history", "travel_history", "family_history"]:
    cnt = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    print(f"  {tbl}: {cnt:,}")
conn.close()
