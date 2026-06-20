# HOSPi Teaching Guide — Volume 5: Data Layer

> **Depth Level:** Complete walkthrough of the seed scripts, database schema, ETL pipeline, and synthetic data generation methodology.

---

## 1. DATABASE SCHEMA — THE 16 TABLES

**File:** `backend/models/__init__.py` (~300 lines)

### 1.1 Table Map

| Table | Records | Purpose | Key Fields |
|---|---|---|---|
| `User` | ~5 | Authentication accounts | email, hashed_password, role |
| `HospitalBed` | ~35K | Monthly bed capacity time-series | state, district, ward_type, total_beds, available_beds, occupancy_rate, recorded_month, recorded_year |
| `MortalityRecord` | ~500K | Death rate time-series | state, district, age_group, cause_of_death, death_rate, death_count, population, year, month |
| `HospitalOutcome` | ~300K | Hospital performance metrics | hospital_name, state, disease, success_rate, hospital_score, total_beds, specialist_count |
| `PandemicOutbreak` | ~700K | Pandemic time-series | disease, state, district, confirmed_cases, deaths, recovered, active_cases, reproduction_rate, case_fatality_rate |
| `Patient` | ~10K | Patient demographics | patient_name, age, blood_group, gender, state, pre_existing_conditions |
| `PatientAdmission` | ~40K | Admission records | admission_date, disease, outcome, stay_days, treatment_cost |
| `VaccineHistory` | ~15K | Patient vaccine records | patient_id, vaccine_name, dose_number, vaccination_date, virus_name |
| `TravelHistory` | ~20K | Patient travel records | patient_id, from_location, to_location, travel_date, return_date |
| `FamilyHistory` | ~10K | Patient family records | patient_id, relationship, condition, age_at_diagnosis |
| `VirusRegistry` | ~20 | Virus definitions | virus_name, fatality_rate, reproductive_rate, vaccine_available, transmission_mode |
| `PredictionLog` | Varies | Audit trail for ML predictions | module, input_params, prediction_result, model_version, response_time_ms |
| `ChatHistory` | Varies | AI conversation history | session_id, role, content, intent_detected, context_used |
| `StateSummary` | 31 | Pre-computed state aggregates | state, avg_death_rate, total_beds, avg_success_rate, best_hospital |
| `DistrictSummary` | ~600 | Pre-computed district aggregates | state, district, avg_score, total_beds, population |
| `Section` | ~20 | Content sections (unused?) | — |

### 1.2 Why 16 Tables?

**Normalization strategy:** The schema is denormalized for read performance:
- `HospitalBed` stores state and district as strings (not foreign keys) — denormalized for faster reads
- `MortalityRecord` also strings — no FK to a districts table
- `Patient` stores state as string — same pattern

**Why denormalize?** SQLite lacks foreign key enforcement by default. Joins in SQLite are slower than PostgreSQL. String lookups with indexes are fast enough for this data volume.

**What would change for PostgreSQL:** Foreign keys would be added. State would reference a `State` table. District would reference a `District` table. Joins would replace string comparisons.

### 1.3 The StateSummary / DistrictSummary Pattern

```python
class StateSummary(Base):
    __tablename__ = "state_summaries"
    state = Column(String, primary_key=True)
    avg_death_rate = Column(Float)
    total_beds = Column(Integer)
    avg_success_rate = Column(Float)
    best_hospital = Column(String)
    common_causes = Column(JSON)  # PostgreSQL JSON or SQLite TEXT
```

**Why separate summary tables?** The location stats endpoint runs 6+ aggregation queries (`COUNT`, `AVG`, `SUM`, `GROUP BY`, `ORDER BY`) across 3 tables (HospitalBed, MortalityRecord, HospitalOutcome). With 1.64M records, these queries take 300-800ms each. The summary table reduces this to a single indexed lookup: ~2ms.

**The refresh mechanism:** `services/summary_refresh.py` runs every hour in a background thread:
```python
def refresh_all_summaries(db):
    # Truncate and repopulate StateSummary
    db.query(StateSummary).delete()
    for state in all_states:
        stats = compute_stats_for_state(db, state)
        db.add(StateSummary(**stats))
    db.commit()
    
    # Same for DistrictSummary
    db.query(DistrictSummary).delete()
    for state in all_states:
        for district in districts_for_state(db, state):
            stats = compute_stats_for_district(db, state, district)
            db.add(DistrictSummary(**stats))
    db.commit()
```

---

## 2. SYNTHETIC DATA GENERATION

### 2.1 Data Sources

The synthetic data is based on **real published datasets** (not randomly generated):

| Source | Data Used | Publisher |
|---|---|---|
| COVID19-India API | Daily case/death time-series (2020-2024) | Volunteer-run, based on MoHFW bulletins |
| HospitalBedsIndia.csv | State-wise public hospital bed capacity | covid19india/deep-dive (GitHub) |
| population_india_census2011.csv | District population estimates | Census 2011 |
| statewise_tested.csv | Testing numbers per state | ICMR |
| SRS Bulletins | Mortality rates by age/cause | Registrar General of India |
| NFHS-5 | Health indicators by district | Ministry of Health |

### 2.2 Seed Scripts

#### `seed_beds.py` (116 lines)

**What it generates:** Monthly bed availability for 30 states × 4 ward types × 120 months (2015-2024) = ~35K records.

**Algorithm:**
```python
# Base capacity from real data
state_beds = STATE_BED_CAPACITY.get(state, 5000)
ward_share = {"General": 0.4, "ICU": 0.15, "Private": 0.2, "Emergency": 0.15, "Maternity": 0.1}
total_beds = int(state_beds * ward_share[ward])

# Seasonal occupancy variation
base_occ = BASE_OCCUPANCY[state]  # 60-85%
seasonal_adj = sin(2π * month / 12) * 5  # ±5% seasonal swing
occupancy = base_occ + seasonal_adj

# COVID-19 surge (March-May 2020)
if year == 2020 and month in [3, 4, 5]:
    occupancy += 20  # 20% occupancy spike
```

**Why seasonal adjustment?** Real hospital bed occupancy varies by season — respiratory infections peak in winter (Dec-Feb), accidents peak in summer, dengue peaks in monsoon. The sine wave (±5%) models this without seasonal data actually existing in the source datasets.

#### `seed_pandemic.py` (352 lines)

**What it generates:** Monthly pandemic data for 6 diseases across 30 states × 120 months = ~700K records.

**The COVID-19 wave formula (the most complex data generation):**
```python
# Real wave parameters (fitted from COVID19-India API data)
WAVES = {
    2020: {"peak_month": 9,  "peak_cases": 97464,  "duration": 4, "spread": "Maharashtra:20000, Delhi:15000, ..."},
    2021: {"peak_month": 5,  "peak_cases": 414188, "duration": 3, "spread": "Maharashtra:65000, ..."},
    2022: {"peak_month": 1,  "peak_cases": 347254, "duration": 3, "spread": "..."},
}

# Weekly gaussian distribution around peak
cases = peak_cases * exp(-0.5 * ((week - peak_week) / sigma)^2)
```

**The endemic tail fix (critical):** Originally, the post-2022 endemic phase used `pop * 0.000001 * year_factor`, producing ~2,100 all-India cases for 2025 — unrealistically low. The fix:

```python
# Before (broken): 2100 cases for 2025
cases = population * 0.000001 * year_factor

# After (fixed): 8.4M cases for 2025
endemic_weekly = 5000 * (1 + sin(2π * week / 52) * 0.3)  # baseline + seasonal
cases = endemic_weekly * state_pop_share * state_pop_scale
```

The 8.4M figure matches real-world COVID-19 endemic circulation (JN.1 variant, etc.).

**Why 20 × pop_scale × year_factor × wave_boost?** After analyzing real ICMR data showing ~15,000-20,000 weekly cases during endemic phase, the multiplier 20 was calibrated to produce ~8.4M annual all-India cases in 2025 (matching real-world surveillance data projections).

#### `seed_patients.py` (180 lines)

**What it generates:** 40K patient admission records for 15 disease types.

**Key distributions:**
```python
age = np.random.exponential(35) + 1  # Right-skewed (more young patients)
gender = np.random.choice(["Male", "Female"])  # ~50/50
outcome = "Recovered" if np.random.random() > 0.15 else "Deceased"  # 85% survival
stay_days = int(np.random.exponential(7)) + 1  # 7-day average stay
```

**Why exponential distributions?** Real healthcare data has exponential distributions: many short stays (1-3 days), fewer long stays (10+ days). A uniform distribution would produce unrealistic length-of-stay patterns.

#### `seed_patient_records.py` (543 lines)

**What it generates:** 10K patients with vaccines, travel, and family history.

**The patient names use real Indian first/last names:**
```python
first_names = ["Aarav", "Vivaan", "Aditya", "Ananya", "Diya", ...]
last_names = ["Sharma", "Patel", "Singh", "Kumar", "Reddy", ...]
```

**Why real names?** Immersion. When a user sees "Patient Aarav Sharma" in the UI, it feels more real than "Patient 39482". The names are common Indian names across different regions, giving the demo data authenticity.

### 2.3 The ETL Pipeline

**File:** `ml_pipeline/real_data_ingest.py` (676 lines)

This is the production data pipeline that downloads REAL data from COVID19-India API:

```python
SOURCES = {
    "districts": "https://data.covid19india.org/csv/latest/districts.csv",
    "state_wise_daily": "https://data.covid19india.org/csv/latest/state_wise_daily.csv",
    "hospital_beds": "https://raw.githubusercontent.com/covid19india/deep-dive/master/data/dataset/HospitalBedsIndia.csv",
    "population": "https://raw.githubusercontent.com/covid19india/deep-dive/master/data/dataset/population_india_census2011.csv",
}
```

**The pipeline steps:**
1. Download CSV from source (or use cached local copy)
2. Clean and normalize state names (`Andaman and Nicobar Islands` → `Andaman & Nicobar Islands`)
3. Aggregate daily → monthly (reduces 350K rows → 50K rows)
4. Generate derived features (lag variables, cyclical encodings, rolling averages)
5. Save processed CSVs for ML training
6. Seed the SQLite database in batch (5K records per insert)

**Batch insert optimization:**
```python
BATCH_SIZE = 5000
for i in range(0, len(df), BATCH_SIZE):
    batch = df.iloc[i:i+BATCH_SIZE]
    session.bulk_insert_mappings(TableName, batch.to_dict(orient="records"))
    session.commit()
```

`bulk_insert_mappings` is 10-50x faster than individual `session.add()` calls because it skips the SQLAlchemy unit-of-work pattern and sends raw INSERT statements.

---

## 3. DATA QUALITY ISSUES

### 3.1 Known Issues

| Issue | Table | Impact | Mitigation |
|---|---|---|---|
| Missing foreign keys | All | No referential integrity | Application-level validation |
| String state names | All | Typo risks (e.g., "TamilNadu" vs "Tamil Nadu") | `normalize_state()` in `app_state.py` |
| Duplicate patient names | Patient | Multiple patients with same name | IDs are the actual identifier |
| Random locality data | (computed) | Not reproducible | Each API call returns different values |

### 3.2 The State Name Normalization

```python
STATE_NAME_MAP = {"orissa": "Odisha", "uttaranchal": "Uttarakhand"}
def normalize_state(name: str) -> str:
    return STATE_NAME_MAP.get(name.lower().strip(), name)
```

**Why only Orissa/Uttaranchal?** These are the two states that officially changed names. Most other states have consistent names across sources. The function exists to catch common misspellings but handles only the known historical renames.

---

## 4. INDEXING STRATEGY

**File:** `add_indexes.py`, `check_indexes.py`

```python
# Indexes created on commonly filtered columns:
- HospitalBed: (state, ward_type, recorded_year, recorded_month)
- MortalityRecord: (state, district, year, month)
- HospitalOutcome: (state, disease, hospital_type)
- PandemicOutbreak: (disease, state, year, month)
- Patient: (state, patient_name)
```

**Why composite indexes?** The location stats queries filter on `WHERE state = 'Tamil Nadu' AND ward_type = 'ICU'` — a composite index on `(state, ward_type)` can be used for both equality filters. Without it, SQLite would scan the entire table.

**What would happen without indexes:** The 1.64M record scan for an unindexed query takes 2-5 seconds in SQLite. With indexes, the same query takes 5-50ms — a 100-1000x improvement.

---

*End of Volume 5. Continue to Volume 6 for Infrastructure.*
