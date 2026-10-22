# Provenance of Epidemic Surveillance Datasets

**Last Verified**: 2026-09-20  
**Target Publication Scope**: IEEE Transactions on Knowledge and Data Engineering / IEEE Transactions on Pattern Analysis and Machine Intelligence / IEEE Transactions on Software Engineering / IEEE JBHI  
**Repository Branch**: `revision-v2`  
**Integrity Phase**: Phase 2C-1 (Authentic Data Reconstruction & Provenance Fix)

---

## 1. Canonical Data Source & Ingestion Provenance

All authentic COVID-19 surveillance data utilized in this reconstruction originates from the official, open-access archive maintained by the **COVID-19 India Tracker** (`covid19india.org`), which aggregated daily bulletins directly from the Ministry of Health and Family Welfare (MoHFW), Government of India, and state health departments.

- **Canonical Repository**: [https://github.com/covid19india/api](https://github.com/covid19india/api)
- **Official Raw Endpoints**:
  - Daily State-Level Time Series: `https://raw.githubusercontent.com/covid19india/api/gh-pages/csv/latest/state_wise_daily.csv`
  - Cumulative District-Level Time Series: `https://raw.githubusercontent.com/covid19india/api/gh-pages/csv/latest/districts.csv`
- **Archival Operational Window**: 2020-03-14 through 2021-10-31 (the project officially halted operations on October 31, 2021, having reconciled 34,284,758 confirmed cases against final MoHFW figures).

---

## 2. Cryptographic Integrity & File Metadata

Every external file in this repository is pinned by an immutable SHA-256 checksum and exact byte count:

| File Path | Description | Rows | Date Range | Size (Bytes) | SHA-256 Hash |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `data/external_verified/state_wise_daily_full_oct2021.csv` | Complete official daily state series (final frozen archive) | 1,791 | 2020-03-14 to 2021-10-31 | 279,211 | `53ccd01ca5fd382e33011fa81ebdaa5074aeacdead5d164a60c7ed6020c94911` |
| `data/external_verified/covid_districts_full_oct2021.csv` | Complete official cumulative district series (final frozen archive) | 358,633 | 2020-04-26 to 2021-10-31 | 19,503,148 | `5458210712b8a30060b8743b0d94e68bb542807c356b0c49cd99bfa2c924d47e` |
| `data/external_verified/state_wise_daily.csv` | Mid-operational snapshot | 1,548 | 2020-03-14 to 2021-08-11 | 243,448 | `de8ea54f3c6cc3aa19b579d93cd626349a457bf70409fe15e87499ed581c6df0` |
| `data/external_verified/districts.csv` | Mid-operational snapshot | 305,930 | 2020-04-26 to 2021-08-12 | 16,034,087 | `afc6432d17894ef926ba932599eb006fa89b9c42de24f31354146bae03007cf6` |
| `ml_pipeline/data/raw/outbreak_real.csv` | **Corrupted legacy file** (synthetic-inflated, fabricated tail) | 17,848 | 1997-01-01 to 2030-12-01 | 1,302,732 | `224b7f38d52105415d3a0e5314f114642d67e693f0c8c0ea8b54ead98d2eed9c` |

### Snapshot Discrepancy Note
The August 2021 snapshot captured data during the active tail of the Delta wave. The October 31, 2021 dataset includes all retroactive audit reconciliations conducted by state governments (accounting for 411 corrected district-day cells out of 305,930 rows) and tracks the post-Delta decline through October 2021. The October 31, 2021 archive is the definitive canonical source.

---

## 3. The Multiplier Locus & Fabrication Deconstruction

Prior audits identified a massive discrepancy where `outbreak_real.csv` reported **249,757,192** COVID-19 cases during the Delta wave alone—more than 12 times India's actual epidemic volume. Code forensics traced the exact mechanism of this inflation and fabrication:

### 3.1 The Order-of-Magnitude (`* 10`) Multiplier
In `scripts/seed_pandemic.py`, function `generate_covid_real()`:
```python
# scripts/seed_pandemic.py:128-129
daily_cases = wave[month]
monthly_cases = int(daily_cases * 30 * state_share * dist_frac * 10)
```
- Here, `daily_cases` was already set to national peak figures (`WAVE2_CASES[4] = 414000`).
- Multiplying `daily_cases * 30` estimated national monthly cases.
- The term was scaled by `state_share * dist_frac` and then explicitly multiplied by `10` (`* 10`).
- Because population share (`state_share`) was assumed uniform across the disease course, populous states with historically lower early test positivity (e.g. Uttar Pradesh, Bihar) received massive synthetic over-allocations.

### 3.2 The Synthetic "Endemic Tail" (2021–2030)
In `scripts/seed_pandemic.py`, lines 260–318:
```python
# scripts/seed_pandemic.py:272
for year in range(2021, 2031):
    for month in range(1, 13):
        if year == 2021 and month <= 7:
            continue
        # Endemic wave pattern: cases decline from 2021 peak to ~20% by 2030
        ...
        rate = 20 * pop_scale * dist_seed * year_factor * season * wave_boost * noise
        confirmed = max(0, int(pop * rate / 100_000))
```
This generated **completely synthetic future data** spanning August 2021 to December 2030 and inserted it into the application database table `pandemic_outbreak`.

### 3.3 False Label Ingestion
In `ml_pipeline/real_outbreak_ingest.py`, function `merge_covid_from_db()`:
```python
# ml_pipeline/real_outbreak_ingest.py:217-224
records.append({
    "date": f"{r.year}-{r.month:02d}-01",
    "disease": "COVID-19",
    "country": "India",
    "state": r.state,
    "confirmed_cases": int(r.confirmed_cases or 0),
    "deaths": int(r.deaths or 0),
    "source": "COVID19-India API", # <--- FALSE LABEL ASSIGNED TO SYNTHETIC TAIL
})
```
All records dumped from the database—including the 2021–2030 synthetic endemic tail and the `* 10` inflated cases—were labeled as `source = "COVID19-India API"`. This file became `ml_pipeline/data/raw/outbreak_real.csv`, contaminating subsequent benchmark evaluations.

---

## 4. Inflation Ratio Analysis: Authentic vs. Contaminated Data

Physical execution comparing `state_wise_daily_full_oct2021.csv` against `outbreak_real.csv` reveals the exact extent of distortion across key epidemic waves:

### 4.1 Delta Wave Surge (April 1, 2021 – July 31, 2021)
| Region / State | Official MoHFW / COVID19-India | Contaminated `outbreak_real.csv` | Inflation Ratio |
| :--- | :---: | :---: | :---: |
| **All-India Total** | **19,433,888** | **249,757,192** | **12.85×** |
| Maharashtra | 3,490,735 | 20,764,047 | 5.95× |
| Delhi | 773,835 | 3,530,478 | 4.56× |
| Karnataka | 1,908,120 | 12,413,785 | 6.51× |
| Tamil Nadu | 1,672,924 | 13,100,372 | 7.83× |
| Uttar Pradesh | 1,091,247 | 47,205,113 | **43.26×** |

### 4.2 Wave 1 Surge (June 1, 2020 – February 28, 2021)
| Region / State | Official MoHFW / COVID19-India | Contaminated `outbreak_real.csv` | Inflation Ratio |
| :--- | :---: | :---: | :---: |
| **All-India Total** | **10,920,692** | **128,386,951** | **11.76×** |
| Maharashtra | 2,087,415 | 10,673,749 | 5.11× |
| Delhi | 619,445 | 1,814,813 | 2.93× |
| Karnataka | 948,030 | 6,381,283 | 6.73× |
| Tamil Nadu | 829,209 | 6,734,221 | 8.12× |
| Uttar Pradesh | 595,452 | 24,265,823 | **40.75×** |

*Note*: The severe distortion in Uttar Pradesh (~41–43×) stems from applying national per-capita scaling uniformly across states without accounting for actual regional reporting delays and clinical testing infrastructure differences during 2020–2021.

---

## 5. Scope of Clean Reconstruction & The Omicron Wave

1. **Clean Period Coverage**:
   - Wave 1: June 2020 through February 2021 (9 months × 30 states = 270 state-months).
   - Delta Wave: April 2021 through July 2021 (4 months × 30 states = 120 state-months).
   - Post-Delta Decline: August 2021 through October 2021 (3 months × 30 states = 90 state-months).
2. **Explicit Omission of the Omicron Wave**:
   - The Omicron variant (B.1.1.529) surged in India between December 2021 and February 2022.
   - The COVID19-India API ceased operations on **October 31, 2021**.
   - Any claims in earlier drafts regarding "Omicron evaluation" were verified to be synthetic or extrapolated. Because no authenticated daily district/state series for Omicron exists within the verified repository archive, **Omicron is excluded from primary benchmark claims** in accordance with integrity guidelines. Future extensions may ingest official MoHFW post-October 2021 bulletins via separate provenance gating.
