"""Seed 2000+ patients with many High-risk patients visible on first pages."""
import sqlite3
import random
from datetime import datetime, timedelta

random.seed(42)

DB_PATH = r"C:\hospi\ml_pipeline\data\hospitaliq.db"

first_names = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Pranav",
    "Ishaan", "Ayaan", "Aryan", "Ravi", "Rajesh", "Sunil", "Vikram",
    "Mohan", "Suresh", "Ramesh", "Dinesh", "Mahesh", "Kishore",
    "Ananya", "Diya", "Myra", "Sara", "Aanya", "Riya", "Ishita",
    "Kavya", "Priya", "Nisha", "Sunita", "Lakshmi", "Radha", "Geeta",
    "Anita", "Sarita", "Meena", "Asha", "Rekha", "Usha",
]
last_names = [
    "Sharma", "Patel", "Singh", "Kumar", "Verma", "Reddy", "Gupta",
    "Joshi", "Nair", "Menon", "Das", "Banerjee", "Choudhury",
    "Iyer", "Pillai", "Rao", "Naidu", "Shah", "Desai", "Mehta",
    "Agarwal", "Malhotra", "Kapoor", "Bhatt", "Saxena",
]
states_list = [
    "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat",
    "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala",
    "Madhya Pradesh", "Maharashtra", "Meghalaya", "Mizoram", "Nagaland",
    "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
    "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Puducherry",
]
blood_groups = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# Condition pools by age group
conditions_young = ["", "", "", "Asthma", "", "", "", "None", "None"]
conditions_mid = ["", "", "Diabetes", "Hypertension", "Thyroid", "", "", "None"]
conditions_elderly = [
    "Diabetes", "Hypertension", "Cardiac", "Diabetes, Hypertension",
    "Hypertension, Obesity", "Diabetes, Cardiac",
    "Diabetes, Hypertension, Obesity", "Cardiac, Hypertension",
    "Diabetes, Renal", "Hypertension, Renal",
    "Diabetes, Hypertension, Cardiac", "Asthma, Hypertension",
    "Thyroid, Diabetes", "Obesity, Hypertension",
    "Diabetes, Hypertension, Cardiac, Obesity",
    "Cardiac, Diabetes, Renal",
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Get max existing ID
cursor.execute("SELECT MAX(id) FROM patients")
max_id = cursor.fetchone()[0] or 0
print(f"Current max patient ID: {max_id}")

# Generate 2000 patients — 60% elderly (60+) with conditions to ensure many show as High
total_new = 2000
records = []

for i in range(total_new):
    pid = max_id + 1 + i
    
    # 50% age 60+ (High or Moderate), 25% age 45-60 (Watch), 25% age under 45 (Low)
    r = random.random()
    if r < 0.50:
        age = random.randint(60, 92)
        condition = random.choice(conditions_elderly)
    elif r < 0.75:
        age = random.randint(45, 59)
        condition = random.choice(conditions_mid)
    else:
        age = random.randint(18, 44)
        condition = random.choice(conditions_young)
    
    gender = random.choice(["Male", "Female"])
    state = random.choice(states_list)
    name = f"{random.choice(first_names)} {random.choice(last_names)}"
    blood = random.choice(blood_groups)
    contact = f"+91-{random.randint(7000000000, 9999999999)}"
    district = f"{state} District"
    dob = datetime.now() - timedelta(days=age * 365 + random.randint(0, 365))
    
    records.append((
        pid, name, dob.strftime("%Y-%m-%d %H:%M:%S"), age, blood,
        gender, contact, "", state, district, condition,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

# Batch insert
BATCH = 500
for i in range(0, len(records), BATCH):
    batch = records[i:i+BATCH]
    placeholders = ",".join("?" * 12)
    cursor.executemany(
        f"INSERT INTO patients (id, patient_name, dob, age, blood_group, gender, contact, address, state, district, pre_existing_conditions, created_at) VALUES ({placeholders})",
        batch
    )
    conn.commit()
    print(f"Inserted {i+len(batch)}/{total_new} patients")

conn.close()

# Verification
conn2 = sqlite3.connect(DB_PATH)
c2 = conn2.cursor()
c2.execute("SELECT COUNT(*) FROM patients")
total = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM patients WHERE age > 65 AND pre_existing_conditions IS NOT NULL AND pre_existing_conditions != '' AND pre_existing_conditions != 'None'")
high = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM patients WHERE age > 65")
old = c2.fetchone()[0]
c2.execute("SELECT COUNT(*) FROM patients WHERE pre_existing_conditions IS NOT NULL AND pre_existing_conditions != '' AND pre_existing_conditions != 'None'")
cond = c2.fetchone()[0]
print(f"\n=== FINAL COUNTS ===")
print(f"Total patients: {total}")
print(f"Age > 65: {old}")
print(f"With conditions: {cond}")
print(f"HIGH risk (age>65 + conditions): {high}")
conn2.close()
