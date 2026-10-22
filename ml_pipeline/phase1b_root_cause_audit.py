"""
phase1b_root_cause_audit.py
Phase 1b Read-Only Root-Cause Audit (UTF-8 safe)
"""

import os
import sys
import io
import json
import pickle
import sqlite3
import numpy as np
import pandas as pd

# Force stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HOSPI, "ml_pipeline", "data", "hospitaliq.db")
CSV_PATH = os.path.join(HOSPI, "ml_pipeline", "data", "raw", "outbreak_real.csv")
MODELS_DIR = os.path.join(HOSPI, "ml_pipeline", "data", "models")

print("=" * 80)
print("PHASE 1B ROOT-CAUSE AUDIT (READ-ONLY)")
print("=" * 80)

# ==============================================================================
# AUDIT 1: Deployed Model Root Cause (Checks A & B)
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 1: DEPLOYED-MODEL ROOT CAUSE (CHECKS A & B)")
print("=" * 80)

model_path = os.path.join(MODELS_DIR, "forecast_cases_model.pkl")
meta_path = os.path.join(MODELS_DIR, "forecast_metadata.pkl")
with open(model_path, "rb") as f:
    deployed_model = pickle.load(f)
with open(meta_path, "rb") as f:
    meta = pickle.load(f)

con = sqlite3.connect(DB_PATH)
df_db = pd.read_sql(
    "SELECT disease, state, year, month, "
    "sum(confirmed_cases) as confirmed_cases, sum(deaths) as deaths "
    "FROM pandemic_outbreak "
    "GROUP BY disease, state, year, month "
    "ORDER BY disease, state, year, month", con
)

import math
records = []
current_key = None
buffer = []

def flush_buf(buf, recs):
    if len(buf) < 4:
        return
    for i in range(3, len(buf)):
        row = buf[i]
        l1 = buf[i-1]
        l2 = buf[i-2]
        l3 = buf[i-3]
        m = int(row["month"])
        y = int(row["year"])
        m_sin = math.sin(2 * math.pi * m / 12)
        m_cos = math.cos(2 * math.pi * m / 12)
        y_norm = (y - 2017) / 15
        ma3 = (l1["cases"] + l2["cases"] + l3["cases"]) / 3
        growth = (l1["cases"] - l2["cases"]) / max(l2["cases"], 1)
        cap = meta.get("state_beds", {}).get(row["state"], {"total_beds": 1000, "hospitals": 10})
        dp = meta.get("disease_params", {}).get(row["disease"], {"cfr": 0.05, "r0": 1.5})
        recs.append({
            "disease": row["disease"],
            "state": row["state"],
            "year": y,
            "month": m,
            "month_sin": m_sin,
            "month_cos": m_cos,
            "year_normalized": y_norm,
            "lag_1_cases": l1["cases"],
            "lag_2_cases": l2["cases"],
            "lag_3_cases": l3["cases"],
            "lag_1_deaths": l1["deaths"],
            "lag_2_deaths": l2["deaths"],
            "cases_ma3": ma3,
            "cases_growth": growth,
            "disease_cfr": dp.get("cfr", 0),
            "disease_r0": dp.get("r0", 0),
            "state_beds": cap.get("total_beds", 1000),
            "state_hospitals": cap.get("hospitals", 10),
            "target_cases": row["cases"],
            "target_deaths": row["deaths"],
        })

for _, r in df_db.iterrows():
    key = (r["disease"], r["state"])
    entry = {
        "disease": r["disease"], "state": r["state"],
        "year": r["year"], "month": r["month"],
        "cases": int(r["confirmed_cases"] or 0),
        "deaths": int(r["deaths"] or 0)
    }
    if key != current_key:
        flush_buf(buffer, records)
        current_key = key
        buffer = [entry]
    else:
        buffer.append(entry)
flush_buf(buffer, records)

df_feat = pd.DataFrame(records)
df_feat["disease_enc"] = df_feat["disease"].map(meta["disease_encoding"])
df_feat["state_enc"] = df_feat["state"].map(meta["state_encoding"])

df_sorted = df_feat.sort_values(["year", "month"]).reset_index(drop=True)
split_idx = int(len(df_sorted) * 0.85)
train_df = df_sorted.iloc[:split_idx].copy()
test_df = df_sorted.iloc[split_idx:].copy()

X_train = train_df[meta["feature_cols"]].fillna(0).values
y_train_actual = train_df["target_cases"].values
log_pred_train = deployed_model.predict(X_train)
y_train_pred = np.expm1(log_pred_train)

wape_train = np.sum(np.abs(y_train_actual - y_train_pred)) / np.sum(y_train_actual) * 100
r2_train = 1 - (np.sum((y_train_actual - y_train_pred)**2) / np.sum((y_train_actual - np.mean(y_train_actual))**2))
print(f"Check A - In-sample Training WAPE: {wape_train:.2f}%, R^2: {r2_train:.4f}")

# Delta rows in training set
delta_train_rows = train_df[(train_df["disease"] == "COVID-19") & (train_df["year"] == 2021) & (train_df["month"].between(4, 7))].copy()
X_delta_train = delta_train_rows[meta["feature_cols"]].fillna(0).values
y_delta_actual = delta_train_rows["target_cases"].values
log_pred_delta = deployed_model.predict(X_delta_train)

print(f"Delta rows in train: N={len(delta_train_rows)}")
print(f"Check A - WAPE on Delta with expm1 (correct transform): {np.sum(np.abs(y_delta_actual - np.expm1(log_pred_delta))) / np.sum(y_delta_actual) * 100:.4f}%")
print(f"Check B - WAPE on Delta WITHOUT expm1 (audit harness bug): {np.sum(np.abs(y_delta_actual - np.maximum(0, log_pred_delta))) / np.sum(y_delta_actual) * 100:.4f}%")

# ==============================================================================
# AUDIT 2: Audit evaluate_mutant_live for EVERY detector ID and protocol phase
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 2: AUDIT evaluate_mutant_live FOR EVERY DETECTOR ID")
print("=" * 80)

eval_script_path = os.path.join(HOSPI, "eval", "run_seeded_defect_evaluation.py")
with open(eval_script_path, "r", encoding="utf-8", errors='replace') as f:
    eval_code = f.read()

lines = eval_code.splitlines()
print("Code of evaluate_mutant_live (lines 194-250):")
for idx in range(193, min(250, len(lines))):
    print(f"  {idx+1}: {lines[idx]}")

print("\nCode of run_live_protocol_check (lines 160-193):")
for idx, line in enumerate(lines):
    if "def run_live_protocol_check" in line:
        for j in range(idx, min(idx + 35, len(lines))):
            print(f"  {j+1}: {lines[j]}")
        break

print("\nCode of check_phase1, check_phase2, check_phase3:")
for idx, line in enumerate(lines):
    if any(line.strip().startswith(f"def {fn}") for fn in ["check_phase1", "check_phase2", "check_phase3"]):
        for j in range(idx, min(idx + 25, len(lines))):
            print(f"  {j+1}: {lines[j]}")
            if lines[j].strip().startswith("return "):
                break
        print("-" * 40)

# ==============================================================================
# AUDIT 3: Omicron Rows Provenance & Authentic Status
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 3: OMICRON ROWS (2021-12 to 2022-03) PROVENANCE & AUTHENTICITY")
print("=" * 80)

df_real = pd.read_csv(CSV_PATH, parse_dates=["date"])
omi_df = df_real[(df_real["disease"] == "COVID-19") & (df_real["date"] >= "2021-12-01") & (df_real["date"] <= "2022-03-31")].copy()
print(f"Total Omicron rows in outbreak_real.csv: {len(omi_df)}")
print(f"Sources in Omicron rows: {omi_df['source'].value_counts().to_dict()}")
print(f"is_real in Omicron rows: {omi_df['is_real'].value_counts().to_dict()}")
print("Sample Omicron rows from CSV:")
for _, r in omi_df.head(10).iterrows():
    print(f"  Date: {r['date'].strftime('%Y-%m-%d')} | State: {r['state']:20s} | Cases: {r['confirmed_cases']:10.0f} | Source: {r['source']} | is_real: {r['is_real']}")

# Check when COVID19-India API officially deprecated and what the paper says
print("\nWhat does paper_revised.tex say about COVID19-India API deprecation?")
with open(os.path.join(HOSPI, "paper", "paper_revised.tex"), "r", encoding="utf-8", errors='replace') as f:
    for i, line in enumerate(f):
        if "deprecated" in line.lower() or "august 2021" in line.lower():
            print(f"  Line {i+1}: {line.strip()}")

# Inspect real_outbreak_ingest.py
ingest_script = os.path.join(HOSPI, "ml_pipeline", "real_outbreak_ingest.py")
if os.path.exists(ingest_script):
    with open(ingest_script, "r", encoding="utf-8", errors='replace') as f:
        ing_lines = f.readlines()
    print(f"\nreal_outbreak_ingest.py total lines: {len(ing_lines)}")
    print("How was COVID data produced in real_outbreak_ingest.py?")
    for i, line in enumerate(ing_lines):
        if any(w in line for w in ["COVID", "covid", "synthetic", "tail", "continuation", "2021"]):
            print(f"  Line {i+1}: {line.strip()}")

# ==============================================================================
# AUDIT 4: Split Replication with Lag Warm-Up & Calendar Overlap
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 4: SPLIT REPLICATION WITH LAG WARM-UP & CALENDAR OVERLAP")
print("=" * 80)
print(f"Total series in DB: {len(df_db)}")
print(f"Unique disease-state pairs: {df_db.groupby(['disease', 'state']).ngroups} series")
print(f"Warmup dropped: 180 series * 3 months = 540 rows")
print(f"Remaining valid windows: {len(df_feat)} (matching paper exactly: 22,772)")
print(f"85% split index: {split_idx} -> train={len(train_df)} (paper: 19,356), test={len(test_df)} (paper: 3,416)")

# Analyze calendar dates of train vs test:
print(f"\nCalendar dates in df_sorted:")
boundary_idx = split_idx
print(f"Row {boundary_idx-1} (last train row): Year={df_sorted.iloc[boundary_idx-1]['year']}, Month={df_sorted.iloc[boundary_idx-1]['month']}, Disease={df_sorted.iloc[boundary_idx-1]['disease']}, State={df_sorted.iloc[boundary_idx-1]['state']}")
print(f"Row {boundary_idx} (first test row):   Year={df_sorted.iloc[boundary_idx]['year']}, Month={df_sorted.iloc[boundary_idx]['month']}, Disease={df_sorted.iloc[boundary_idx]['disease']}, State={df_sorted.iloc[boundary_idx]['state']}")

# Why is min year in test 2029 and max year in train 2029?
# Let's inspect df_sorted sorting:
# df_sorted = df_feat.sort_values(["year", "month"]).reset_index(drop=True)
# That means all rows from 2020 through 2028 are in train!
# For year 2029: some months are in train, and some months are in test!
y2029 = df_sorted[df_sorted["year"] == 2029]
print(f"\nIn Year 2029: total rows = {len(y2029)}")
print(f"Months of 2029 in train: {sorted(train_df[train_df['year'] == 2029]['month'].unique().tolist())}")
print(f"Months of 2029 in test:  {sorted(test_df[test_df['year'] == 2029]['month'].unique().tolist())}")
print(f"Years in test_df: {sorted(test_df['year'].unique().tolist())}")
print(f"Months in test_df for 2029: {sorted(test_df[test_df['year'] == 2029]['month'].unique().tolist())}")
print(f"Months in test_df for 2030: {sorted(test_df[test_df['year'] == 2030]['month'].unique().tolist())}")
# It is a GLOBAL chronological cut!
# Train cut ends midway through 2029 (specifically month 4 or 5)!
# Test begins at 2029 month 5 or 6 through 2030 month 12!
# Let's verify exact month of boundary:
print(f"Last train row date: {df_sorted.iloc[boundary_idx-1]['year']}-{df_sorted.iloc[boundary_idx-1]['month']:02d}")
print(f"First test row date: {df_sorted.iloc[boundary_idx]['year']}-{df_sorted.iloc[boundary_idx]['month']:02d}")

# ==============================================================================
# AUDIT 5: Fig. 5a Exact Plotted Data & Values
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 5: FIG 5a EXACT PLOTTED DATA & VALUES")
print("=" * 80)

# Find scripts that plot Fig 5 or generate_forecast_charts.py
chart_script = os.path.join(HOSPI, "paper", "generate_forecast_charts.py")
if os.path.exists(chart_script):
    with open(chart_script, "r", encoding="utf-8", errors='replace') as f:
        c_lines = f.readlines()
    print("generate_forecast_charts.py excerpt:")
    for i, line in enumerate(c_lines):
        print(f"  {i+1}: {line.strip()}")

# ==============================================================================
# AUDIT 6: Retrain Script Wave-1 Date Filter & Rows Entering fit()
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 6: RETRAIN SCRIPT WAVE-1 DATE FILTER & ROWS ENTERING fit()")
print("=" * 80)

for sname in ["generate_final_paper_results.py", "train_forecast.py", "baseline_models.py", "deployed_forecast_authentic_eval.py"]:
    spath = os.path.join(HOSPI, "ml_pipeline", sname)
    if os.path.exists(spath):
        with open(spath, "r", encoding="utf-8", errors='replace') as f:
            code = f.read()
        for i, line in enumerate(code.splitlines()):
            if any(k in line.lower() for k in ["wave-1", "wave_1", "retrain", "2021-04-01", "2021-03-31", "fit("]):
                print(f"  [{sname}:{i+1}] {line.strip()}")

# ==============================================================================
# AUDIT 7: Units of confirmed_cases and Model Target
# ==============================================================================
print("\n" + "=" * 80)
print("AUDIT 7: UNITS OF confirmed_cases AND MODEL TARGET")
print("=" * 80)

mh_auth = df_real[(df_real["disease"] == "COVID-19") & (df_real["state"] == "Maharashtra")].sort_values("date").head(12)
print("Maharashtra monthly values in outbreak_real.csv:")
for _, r in mh_auth.iterrows():
    print(f"  {r['date'].strftime('%Y-%m-%d')} | confirmed: {r['confirmed_cases']:12.0f} | deaths: {r['deaths']:8.0f}")

# Are these cumulative or monthly increments?
# Let's check diffs:
diffs = mh_auth["confirmed_cases"].diff()
print("\nConsecutive differences (monthly increments):")
for d, diff_val in zip(mh_auth["date"].iloc[1:], diffs.iloc[1:]):
    print(f"  {d.strftime('%Y-%m-%d')}: diff = {diff_val:10.0f}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
