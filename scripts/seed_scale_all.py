"""Scale 4 tables to 100K+ records each with realistic Indian data.
Uses batch inserts for performance. Maintains real-world ratios."""
import sqlite3, random, os, sys, time
from datetime import datetime, date, timedelta


from backend.config import settings

DB = settings.database_url.replace("sqlite:///", "")
if not os.path.isabs(DB):
    DB = os.path.join(os.path.dirname(__file__), DB)

random.seed(42)
t_start = time.time()
BATCH = 10000
now_iso = datetime.now().isoformat()

conn = sqlite3.connect(DB)
c = conn.cursor()

# ── Realistic Indian data sources ──────────────────────────────────
STATES = [
    ("Uttar Pradesh", 0.165), ("Maharashtra", 0.095), ("Bihar", 0.085),
    ("West Bengal", 0.075), ("Madhya Pradesh", 0.065), ("Tamil Nadu", 0.060),
    ("Rajasthan", 0.060), ("Karnataka", 0.055), ("Gujarat", 0.050),
    ("Andhra Pradesh", 0.040), ("Odisha", 0.035), ("Telangana", 0.030),
    ("Kerala", 0.030), ("Jharkhand", 0.030), ("Assam", 0.030),
    ("Punjab", 0.028), ("Chhattisgarh", 0.025), ("Haryana", 0.022),
    ("Delhi", 0.018), ("Jammu and Kashmir", 0.015), ("Uttarakhand", 0.010),
    ("Himachal Pradesh", 0.008), ("Tripura", 0.004), ("Meghalaya", 0.003),
    ("Manipur", 0.003), ("Nagaland", 0.002), ("Goa", 0.002),
    ("Arunachal Pradesh", 0.002), ("Mizoram", 0.001), ("Sikkim", 0.001),
]
STATE_NAMES = [s for s, _ in STATES]
STATE_WTS  = [w for _, w in STATES]

DISTRICTS_PER_STATE = {
    "Uttar Pradesh": ["Lucknow","Kanpur","Agra","Varanasi","Allahabad","Meerut","Ghaziabad","Noida","Bareilly","Aligarh","Moradabad","Gorakhpur","Bulandshahr","Saharanpur","Mathura","Firozabad","Azamgarh","Shahjahanpur","Rampur","Sitapur"],
    "Maharashtra": ["Mumbai","Pune","Nagpur","Thane","Nashik","Aurangabad","Solapur","Kolhapur","Satara","Sangli","Amravati","Chandrapur","Jalgaon","Dhule","Latur","Ratnagiri","Nanded","Wardha","Osmanabad","Yavatmal"],
    "Bihar": ["Patna","Gaya","Bhagalpur","Muzaffarpur","Darbhanga","Purnia","Bihar Sharif","Arrah","Begusarai","Chapra","Katihar","Munger","Sasaram","Hajipur","Bettiah","Motihari","Saharsa","Madhubani","Samastipur","Siwan"],
    "West Bengal": ["Kolkata","Darjeeling","Hooghly","Howrah","Bardhaman","Nadia","Murshidabad","Midnapore","Jalpaiguri","Cooch Behar","Bankura","Birbhum","Malda","Siliguri","Asansol","Durgapur","Kharagpur","Haldia","Krishnanagar","Balurghat"],
    "Madhya Pradesh": ["Bhopal","Indore","Gwalior","Jabalpur","Ujjain","Sagar","Dewas","Satna","Ratlam","Rewa","Murwara","Singrauli","Burhanpur","Khandwa","Chhindwara","Damoh","Mandsaur","Neemuch","Shivpuri","Vidisha"],
    "Tamil Nadu": ["Chennai","Coimbatore","Madurai","Tiruchirappalli","Salem","Tirunelveli","Vellore","Erode","Thoothukudi","Dindigul","Kancheepuram","Virudhunagar","Cuddalore","Villupuram","Thanjavur","Nagapattinam","Ramanathapuram","Nagercoil","Tiruvannamalai","Dharmapuri"],
    "Karnataka": ["Bangalore","Mysore","Hubli","Mangalore","Belgaum","Gulbarga","Davangere","Shimoga","Tumkur","Udupi","Hassan","Raichur","Bidar","Bellary","Chitradurga","Chikmagalur","Mandya","Kolar","Hospet","Karwar"],
    "Rajasthan": ["Jaipur","Jodhpur","Udaipur","Kota","Bikaner","Ajmer","Alwar","Bhilwara","Sikar","Bharatpur","Pali","Jhunjhunu","Churu","Ganganagar","Banswara","Baran","Bundi","Dausa","Jhalawar","Nagaur"],
    "Gujarat": ["Ahmedabad","Surat","Vadodara","Rajkot","Bhavnagar","Jamnagar","Junagadh","Gandhinagar","Anand","Navsari","Surendranagar","Bharuch","Mehsana","Nadiad","Morbi","Bhuj","Valsad","Patan","Porbandar","Godhra"],
    "Andhra Pradesh": ["Visakhapatnam","Vijayawada","Guntur","Nellore","Kurnool","Kakinada","Rajahmundry","Tirupati","Anantapur","Eluru","Ongole","Kadapa","Chittoor","Machilipatnam","Tenali","Proddatur","Hindupur","Madanapalle","Srikakulam","Vizianagaram"],
    "Odisha": ["Bhubaneswar","Cuttack","Rourkela","Berhampur","Sambalpur","Puri","Balasore","Bhadrak","Baripada","Jharsuguda","Barbil","Jeypore","Paradeep","Angul","Dhenkanal","Kendrapara","Jajpur","Nayagarh","Phulbani","Koraput"],
    "Telangana": ["Hyderabad","Warangal","Nizamabad","Karimnagar","Khammam","Ramagundam","Mahbubnagar","Nalgonda","Adilabad","Siddipet","Medak","Medchal","Jagitial","Mancherial","Suryapet","Wanaparthy","Vikarabad","Bhadradri","Jangaon","Kamareddy"],
    "Kerala": ["Thiruvananthapuram","Kochi","Kozhikode","Thrissur","Alappuzha","Kollam","Palakkad","Kannur","Kottayam","Malappuram","Pathanamthitta","Wayanad","Idukki","Kasaragod","Ernakulam","Kalamassery","Changanassery","Kothamangalam","Perumbavoor","North Paravur"],
    "Jharkhand": ["Ranchi","Jamshedpur","Dhanbad","Bokaro","Deoghar","Hazaribagh","Giridih","Ramgarh","Dumka","Phusro","Chaibasa","Lohardaga","Pakur","Sahebganj","Simdega","Latehar","Garhwa","Godda","Koderma","Jamtara"],
    "Assam": ["Guwahati","Silchar","Dibrugarh","Jorhat","Nagaon","Tinsukia","Tezpur","Barpeta","Bongaigaon","Goalpara","Hailakandi","Karimganj","Kokrajhar","Lakhimpur","Sivasagar","Sonitpur","Dhemaji","Golaghat","Majuli","Morigaon"],
    "Punjab": ["Ludhiana","Amritsar","Jalandhar","Patiala","Bathinda","Mohali","Hoshiarpur","Batala","Pathankot","Moga","Firozpur","Kapurthala","Ropar","Sangrur","Barnala","Faridkot","Fatehgarh Sahib","Gurdaspur","Mansa","Nawanshahr"],
    "Chhattisgarh": ["Raipur","Bhilai","Bilaspur","Korba","Durg","Rajnandgaon","Raigarh","Ambikapur","Jagdalpur","Dhamtari","Mahasamund","Kanker","Dantewada","Kawardha","Sukma","Narayanpur","Balod","Bemetara","Kondagaon","Mungeli"],
    "Haryana": ["Chandigarh","Faridabad","Gurgaon","Panipat","Ambala","Karnal","Sonipat","Yamunanagar","Rohtak","Hisar","Rewari","Bhiwani","Sirsa","Kaithal","Jind","Kurukshetra","Palwal","Fatehabad","Nuh","Panchkula"],
    "Delhi": ["Central Delhi","South Delhi","East Delhi","North Delhi","West Delhi","New Delhi","Shahdara","North West Delhi","South East Delhi","South West Delhi","North East Delhi","Rohini","Dwarka","Patparganj","Karol Bagh","Chandni Chowk","Saket","Lajpat Nagar","Janakpuri","Pitampura"],
    "Jammu and Kashmir": ["Srinagar","Jammu","Anantnag","Baramulla","Kupwara","Pulwama","Budgam","Ganderbal","Bandipora","Kulgam","Rajouri","Poonch","Doda","Ramban","Kishtwar","Samba","Kathua","Reasi","Shopian","Udhampur"],
    "Uttarakhand": ["Dehradun","Haridwar","Rishikesh","Nainital","Haldwani","Roorkee","Rudrapur","Kashipur","Almora","Pithoragarh","Pauri","Tehri","Champawat","Bageshwar","Rudraprayag","Chamoli","Uttarkashi","Kotdwar","Ramnagar","Mukteshwar"],
    "Goa": ["North Goa","South Goa","Panaji","Margao","Vasco","Mapusa","Ponda","Bicholim","Canacona","Pernem","Sanguem","Quepem","Curchorem","Shiroda","Valpoi","Dabolim","Navelim","Calangute","Candolim","Porvorim"],
}
ALL_DISTRICTS = []
for dlist in DISTRICTS_PER_STATE.values():
    ALL_DISTRICTS.extend(dlist)

HOSPITAL_TYPES = ["Govt","Private","Trust","NGO"]
DISEASES = ["Cardiac","Diabetes","Dengue","Tuberculosis","Pneumonia","Cancer","Stroke","Hepatitis","Malaria","Typhoid","Renal","Orthopedic"]
DISEASE_STAY = {"Cardiac":(5,15),"Diabetes":(2,8),"Dengue":(3,10),"Tuberculosis":(10,30),"Pneumonia":(3,12),"Cancer":(5,20),"Stroke":(4,14),"Hepatitis":(4,12),"Malaria":(2,8),"Typhoid":(3,10),"Renal":(4,15),"Orthopedic":(3,14)}
DISEASE_MORTALITY = {"Cardiac":0.06,"Diabetes":0.015,"Dengue":0.008,"Tuberculosis":0.04,"Pneumonia":0.05,"Cancer":0.12,"Stroke":0.09,"Hepatitis":0.02,"Malaria":0.005,"Typhoid":0.01,"Renal":0.05,"Orthopedic":0.01}
TYPE_SUCCESS = {"Govt":0.78,"Private":0.87,"Trust":0.80,"NGO":0.76}
HOSPITAL_HUMAN_SUFFIX = ["Hospital","Medical Centre","Clinic","Nursing Home","Institute"]
ACC_POOL = ["NABH","JCI","ISO","None"]
ACC_WT   = [0.04, 0.01, 0.15, 0.80]

# Age groups with realistic Indian distribution for admissions
AGE_GROUPS = ["0-14","15-44","45-64","65+"]
AGE_WT = [0.25, 0.43, 0.22, 0.10]
AGE_BY_DISEASE = {
    "Cardiac": [0.02,0.20,0.45,0.33], "Diabetes": [0.03,0.25,0.42,0.30],
    "Dengue": [0.25,0.45,0.20,0.10], "Tuberculosis": [0.08,0.40,0.32,0.20],
    "Pneumonia": [0.20,0.25,0.30,0.25], "Cancer": [0.03,0.18,0.40,0.39],
    "Stroke": [0.01,0.12,0.38,0.49], "Hepatitis": [0.08,0.45,0.30,0.17],
    "Malaria": [0.20,0.45,0.22,0.13], "Typhoid": [0.18,0.45,0.22,0.15],
    "Renal": [0.05,0.22,0.40,0.33], "Orthopedic": [0.05,0.25,0.35,0.35],
}
# Monthly admission multipliers (seasonal)
SEASONAL = {1:1.15,2:1.10,3:1.05,4:0.95,5:0.88,6:0.85,7:0.88,8:0.92,9:0.95,10:1.00,11:1.08,12:1.12}

# ── Clear old data ────────────────────────────────────────────────
for tbl in ["hospital_outcomes","patient_admissions","travel_history","family_history"]:
    c.execute(f"DELETE FROM [{tbl}]")
conn.commit()

# ── 1. HOSPITAL OUTCOMES ──────────────────────────────────────────
print("=== Hospital Outcomes (3,200 → 100K+) ===")
t0 = time.time()
hosp_batch = []
hid = 1
total_hospitals = 0
# Hospital weight per state (proportional to population)
STATE_HOSP_WT = {"Uttar Pradesh": 2800, "Maharashtra": 2100, "Bihar": 1200, "West Bengal": 1500, "Madhya Pradesh": 1400, "Tamil Nadu": 1800, "Rajasthan": 1600, "Karnataka": 2200, "Gujarat": 1900, "Andhra Pradesh": 1000, "Odisha": 900, "Telangana": 900, "Kerala": 1200, "Jharkhand": 600, "Assam": 700, "Punjab": 700, "Chhattisgarh": 500, "Haryana": 600, "Delhi": 400, "Jammu and Kashmir": 500, "Uttarakhand": 250, "Himachal Pradesh": 300, "Tripura": 80, "Meghalaya": 80, "Manipur": 80, "Nagaland": 60, "Goa": 70, "Arunachal Pradesh": 50, "Mizoram": 50, "Sikkim": 30}
# Cap per district proportional to state size
STATE_HOSP_CAP = {"Uttar Pradesh": 150, "Maharashtra": 120, "Bihar": 80, "West Bengal": 80, "Madhya Pradesh": 80, "Tamil Nadu": 100, "Rajasthan": 80, "Karnataka": 120, "Gujarat": 100, "Andhra Pradesh": 60, "Odisha": 50, "Telangana": 50, "Kerala": 70, "Jharkhand": 40, "Assam": 40, "Punjab": 40, "Chhattisgarh": 30, "Haryana": 35, "Delhi": 25, "Jammu and Kashmir": 30, "Uttarakhand": 20, "Himachal Pradesh": 20, "Tripura": 10, "Meghalaya": 10, "Manipur": 10, "Nagaland": 8, "Goa": 8, "Arunachal Pradesh": 8, "Mizoram": 8, "Sikkim": 5}

for state in STATE_NAMES:
    districts = DISTRICTS_PER_STATE.get(state, ["Central District"])
    ndist = len(districts)
    target_hospitals = STATE_HOSP_WT.get(state, 200)
    cap = STATE_HOSP_CAP.get(state, 30)
    # Distribute hospitals across districts proportional to state population
    n_per_dist = max(2, min(cap, target_hospitals // ndist))
    for dist in districts:
        for h in range(n_per_dist):
            suffix = random.choice(HOSPITAL_HUMAN_SUFFIX)
            hname = f"{state} {dist} {suffix} {chr(65+random.randint(0,25))}"
            htype = random.choices(HOSPITAL_TYPES, weights=[0.25,0.45,0.20,0.10])[0]
            base_success = TYPE_SUCCESS[htype]
            total_beds = min(800, max(20, int(random.lognormvariate(4.5, 0.6))))
            icu = max(2, int(total_beds * 0.08))
            specialist = max(1, int(total_beds * 0.04))
            acc = random.choices(ACC_POOL, weights=ACC_WT)[0]

            for disease in DISEASES:
                adj = 0
                if disease in ("Cardiac","Stroke"): adj = 0.03
                elif disease in ("Cancer","Tuberculosis"): adj = -0.02
                elif disease in ("Diabetes","Renal"): adj = 0.02
                sr = min(0.95, max(0.60, base_success + adj + random.gauss(0, 0.03)))
                tc = random.randint(50, 800)
                succ = int(tc * sr)
                stay_min, stay_max = DISEASE_STAY.get(disease, (3, 10))
                avg_stay = round(random.uniform(stay_min, stay_max), 1)
                acc_score = {"NABH":3,"JCI":3,"ISO":2,"None":1}[acc]
                hscore = round(sr * 0.5 + (1/avg_stay) * 0.3 + acc_score/5 * 0.2, 4)
                rating = min(round(hscore * 1.25, 2), 5.0)

                hosp_batch.append((
                    f"HOSP_{hid:04d}", hname, state, dist, htype,
                    disease, tc, succ, tc-succ, round(sr, 4),
                    avg_stay, total_beds, icu, specialist, acc, hscore, rating, now_iso
                ))

            hid += 1
            total_hospitals += 1

    if len(hosp_batch) >= BATCH:
        c.executemany("""
            INSERT INTO hospital_outcomes 
            (hospital_id,hospital_name,state,district,hospital_type,disease,
             total_cases,success_count,failure_count,success_rate,avg_stay_days,
             total_beds,icu_beds,specialist_count,accreditation,hospital_score,rating,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, hosp_batch)
        conn.commit()
        if total_hospitals % 5000 == 0:
            print(f"  {total_hospitals} hospitals processed ({time.time()-t0:.1f}s)")
        hosp_batch = []

if hosp_batch:
    c.executemany("""
        INSERT INTO hospital_outcomes 
        (hospital_id,hospital_name,state,district,hospital_type,disease,
         total_cases,success_count,failure_count,success_rate,avg_stay_days,
         total_beds,icu_beds,specialist_count,accreditation,hospital_score,rating,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, hosp_batch)
    conn.commit()

hosp_total = total_hospitals * len(DISEASES)
print(f"[OK] {hosp_total:,} records ({total_hospitals:,} hospitals × {len(DISEASES)} diseases) in {time.time()-t0:.1f}s")

# ── 2. PATIENT ADMISSIONS ─────────────────────────────────────────
print("\n=== Patient Admissions (40,000 → 100K+) ===")
t0 = time.time()
NUM_ADM = 100_000
adm_batch = []
YEARS = [2018,2019,2020,2021,2022,2023,2024]
COVID_MONTHS = {(2020,3),(2020,4),(2020,5),(2020,6),(2020,7),(2020,8),(2020,9),(2020,10),(2020,11),(2020,12),(2021,1),(2021,2),(2021,3),(2021,4),(2021,5),(2021,6)}

for i in range(1, NUM_ADM + 1):
    state = random.choices(STATE_NAMES, weights=STATE_WTS)[0]
    districts = DISTRICTS_PER_STATE.get(state, ["Central District"])
    district = random.choice(districts)
    
    year = random.choice(YEARS)
    month = random.randint(1, 12)
    # Apply seasonal weight
    r = random.random() * sum(SEASONAL.values())
    cum = 0
    for m, w in SEASONAL.items():
        cum += w
        if r <= cum:
            month = m
            break
    
    # Disease selection with seasonal/COVID influence
    disease = random.choice(DISEASES)
    if (year, month) in COVID_MONTHS and random.random() < 0.3:
        disease = random.choice(["Pneumonia","Tuberculosis"])
    
    # Age based on disease
    age_dist = AGE_BY_DISEASE.get(disease, AGE_WT)
    age_group = random.choices(AGE_GROUPS, weights=age_dist)[0]
    gender = "F" if disease in ["Maternal"] and random.random() < 0.8 else random.choice(["M","F"])
    
    day = random.randint(1, 28)
    adm_date = date(year, month, day)
    stay_min, stay_max = DISEASE_STAY.get(disease, (3, 10))
    stay = max(1, int(random.gauss((stay_min + stay_max) / 2, (stay_max - stay_min) / 3)))
    dis_date = adm_date + timedelta(days=stay)
    
    # Outcome
    mort_rate = DISEASE_MORTALITY.get(disease, 0.03)
    if age_group in ("45-64","65+"):
        mort_rate *= 1.3 if age_group == "45-64" else 1.8
    if disease in ("Pneumonia","Tuberculosis") and (year, month) in COVID_MONTHS:
        mort_rate *= 2.0
    outcome = "deceased" if random.random() < mort_rate else random.choice(["recovered","transferred","recovered","recovered"])
    
    # Cost
    base = random.randint(15000, 350000)
    if disease in ("Cardiac","Cancer","Stroke"):
        base = int(base * 1.8)
    elif disease in ("Renal","Orthopedic"):
        base = int(base * 1.3)
    if age_group in ("45-64","65+"):
        base = int(base * 1.2)
    cost = int(base * random.uniform(0.7, 1.3))
    
    admit_type = random.choices(["emergency","planned"], weights=[0.55, 0.45])[0]
    insurance = random.choices(["Government","Private","None"], weights=[0.35, 0.40, 0.25])[0]
    pid = f"PAT_{i:06d}"
    hosp_name = f"{state} {district} Hospital"
    
    adm_batch.append((
        pid, adm_date.isoformat(), dis_date.isoformat(),
        f"HOSP_{random.randint(1, total_hospitals):04d}", hosp_name, state,
        disease, age_group, gender, admit_type, outcome, stay, cost, insurance, now_iso
    ))
    
    if len(adm_batch) >= BATCH:
        c.executemany("""
            INSERT INTO patient_admissions 
            (patient_id,admission_date,discharge_date,hospital_id,hospital_name,state,
             disease,age_group,gender,admission_type,outcome,stay_days,treatment_cost,insurance_type,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, adm_batch)
        conn.commit()
        if i % 30000 == 0:
            print(f"  {i:,} admissions... ({time.time()-t0:.1f}s)")
        adm_batch = []

if adm_batch:
    c.executemany("INSERT INTO patient_admissions (patient_id,admission_date,discharge_date,hospital_id,hospital_name,state,disease,age_group,gender,admission_type,outcome,stay_days,treatment_cost,insurance_type,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", adm_batch)
    conn.commit()
print(f"[OK] {NUM_ADM:,} admissions created ({time.time()-t0:.1f}s)")

# ── 3. TRAVEL HISTORY ──────────────────────────────────────────────
print("\n=== Travel History (52K → 100K+) ===")
t0 = time.time()
IN_CITIES = ["Mumbai","Delhi","Bangalore","Hyderabad","Chennai","Kolkata","Pune","Ahmedabad","Jaipur","Lucknow","Surat","Bhopal","Patna","Indore","Nagpur","Chandigarh","Kochi","Bhubaneswar","Guwahati","Thiruvananthapuram"]
OUT_CITIES = ["Dubai","Bangkok","Singapore","London","New York","Toronto","Sydney","Kuala Lumpur","Sharjah","Riyadh","Doha","Muscat","Colombo","Kathmandu","Dhaka","Melbourne","Paris","Frankfurt","Chicago","San Francisco"]
PURPOSES = ["Business","Tourism","Medical","Education","Family Visit","Pilgrimage"]

trav_batch = []
trav_total = 0
for pid in range(1, 200001):
    # 35% probability of having at least 1 trip
    if random.random() < 0.35:
        n_trips = random.choices([1,2,3,4], weights=[50,30,15,5])[0]
        for _ in range(n_trips):
            from_city = random.choice(IN_CITIES)
            candidates = [c for c in (IN_CITIES + OUT_CITIES) if c != from_city]
            to_city = random.choice(candidates)
            days_ago = random.randint(20, 500)
            start = date.today() - timedelta(days=days_ago)
            dur = random.randint(2, 25)
            end = start + timedelta(days=dur)
            purpose = random.choice(PURPOSES)
            trav_batch.append((pid, from_city, to_city, start.isoformat(), end.isoformat(), purpose, now_iso))
            trav_total += 1
    
    if len(trav_batch) >= BATCH:
        c.executemany("INSERT INTO travel_history (patient_id,from_location,to_location,travel_date,return_date,purpose,created_at) VALUES (?,?,?,?,?,?,?)", trav_batch)
        conn.commit()
        trav_batch = []

if trav_batch:
    c.executemany("INSERT INTO travel_history (patient_id,from_location,to_location,travel_date,return_date,purpose,created_at) VALUES (?,?,?,?,?,?,?)", trav_batch)
    conn.commit()
print(f"[OK] {trav_total:,} travel records ({time.time()-t0:.1f}s)")

# ── 4. FAMILY HISTORY ──────────────────────────────────────────────
print("\n=== Family History (38K → 100K+) ===")
t0 = time.time()
FAM_COND = ["Diabetes","Cardiac","Cancer","Hypertension","Asthma","Stroke","Renal Disease","Thyroid"]
FAM_REL = ["Father","Mother","Brother","Sister","Grandfather","Grandmother","Uncle","Aunt"]

fam_batch = []
fam_total = 0
for pid in range(1, 200001):
    # 35% probability of having family history entries
    if random.random() < 0.35:
        n_fam = random.choices([1,2,3], weights=[55,30,15])[0]
        for _ in range(n_fam):
            rel = random.choice(FAM_REL)
            cond = random.choice(FAM_COND)
            diag = random.randint(20, 80)
            deceased = random.random() < 0.3
            fam_batch.append((pid, rel, cond, diag, deceased, now_iso))
            fam_total += 1
    
    if len(fam_batch) >= BATCH:
        c.executemany("INSERT INTO family_history (patient_id,relationship,condition,age_at_diagnosis,is_deceased,created_at) VALUES (?,?,?,?,?,?)", fam_batch)
        conn.commit()
        fam_batch = []

if fam_batch:
    c.executemany("INSERT INTO family_history (patient_id,relationship,condition,age_at_diagnosis,is_deceased,created_at) VALUES (?,?,?,?,?,?)", fam_batch)
    conn.commit()
print(f"[OK] {fam_total:,} family history records ({time.time()-t0:.1f}s)")

# ── Summary ────────────────────────────────────────────────────────
t_elapsed = time.time() - t_start
print(f"\n{'='*50}")
print(f"Total time: {t_elapsed:.1f}s")
print(f"{'='*50}")
for tbl in ["hospital_outcomes","patient_admissions","travel_history","family_history"]:
    cnt = conn.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
    print(f"  {tbl}: {cnt:,}")
# Grand total
gt = conn.execute("""
    SELECT SUM(cnt) FROM (
        SELECT COUNT(*) cnt FROM hospital_outcomes UNION ALL
        SELECT COUNT(*) FROM patient_admissions UNION ALL
        SELECT COUNT(*) FROM travel_history UNION ALL
        SELECT COUNT(*) FROM family_history
    )
""").fetchone()[0]
print(f"  Combined new records: {gt:,}")
conn.close()
print("\nDone!")
