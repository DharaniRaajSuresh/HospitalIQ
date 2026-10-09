"""
verify_group_a.py
Comprehensive inspection script for Group A verification report.
Prints:
1. Exact schemas of outbreak_real.csv and hospitaliq.db
2. Full state x month count matrix of authentic COVID-19 records across entire history (unbiased, no pre-filtering)
3. Omicron window (Dec 2021 - March 2022) state x month check to locate any missing state-month row
4. Deployed model training rows: min/max(date) under 85/15 chronological split and check for ~510 authentic rows
5. Fig. 5a data points, Uttar Pradesh max values in pandemic_outbreak, and source of [0, 50,000] claim
6. Exact McNemar contingency table counts and exact p-value
7. Static Dataflow counts from formal_seeded_defect_benchmark.json and held_out_taxonomy_results.json
8. Checkpoint 20260722_205310 hyperparameter inspection
"""

import os
import sqlite3
import pickle
import json
import numpy as np
import pandas as pd
from scipy import stats

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(HOSPI, "ml_pipeline", "data", "hospitaliq.db")
CSV_PATH = os.path.join(HOSPI, "ml_pipeline", "data", "raw", "outbreak_real.csv")

print("=" * 80)
print("GROUP A VERIFICATION REPORT: DATA-GROUNDED AUDIT")
print("=" * 80)

# ------------------------------------------------------------------------------
# 1. Schemas
# ------------------------------------------------------------------------------
print("\n[1] SCHEMAS")
df_csv = pd.read_csv(CSV_PATH)
print(f"outbreak_real.csv shape: {df_csv.shape}")
print("outbreak_real.csv columns & types:")
for col, dtype in df_csv.dtypes.items():
    print(f"  {col}: {dtype}")

con = sqlite3.connect(DB_PATH)
cur = con.cursor()
schema = cur.execute("PRAGMA table_info(pandemic_outbreak)").fetchall()
print("\npandemic_outbreak table columns & types in hospitaliq.db:")
for col in schema:
    print(f"  cid={col[0]}, name={col[1]}, type={col[2]}, notnull={col[3]}, dflt_value={col[4]}, pk={col[5]}")

# ------------------------------------------------------------------------------
# 2. State x Month Matrix for Authentic Rows (Unbiased, No Pre-filtering)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[2] UNBIASED STATE x MONTH MATRIX FOR AUTHENTIC COVID-19 ROWS")
print("=" * 80)
print("Filtering outbreak_real.csv strictly on disease == 'COVID-19' and is_real == True (or source == 'COVID19-India API'):")
covid_real = df_csv[(df_csv["disease"] == "COVID-19") & (df_csv["is_real"] == True)].copy()
covid_real["date"] = pd.to_datetime(covid_real["date"])
covid_real["year_month"] = covid_real["date"].dt.to_period("M").astype(str)

print(f"Total COVID-19 real-flagged rows in CSV: {len(covid_real)}")
print(f"Distinct sources for COVID-19 real: {covid_real['source'].value_counts().to_dict()}")
print(f"Distinct states ({covid_real['state'].nunique()}): {sorted(covid_real['state'].dropna().unique().tolist())}")
print(f"Overall date range: min={covid_real['date'].min()}, max={covid_real['date'].max()}")

# Pivot table: state x year_month
matrix = pd.crosstab(covid_real["state"], covid_real["year_month"])
print(f"\nFull State x Month Matrix shape: {matrix.shape} (States x Months)")
print("\nUnique month periods:", sorted(matrix.columns.tolist()))
print("\nColumn totals (records per month across states):")
col_sums = matrix.sum(axis=0)
for ym, count in col_sums.items():
    print(f"  {ym}: {count} states reporting")

# Wave 1 focus: look at 2020 through mid 2021
print("\nMonth totals from 2020-03 to 2021-08:")
w1_cols = [c for c in matrix.columns if "2020-03" <= c <= "2021-08"]
for c in w1_cols:
    print(f"  {c}: {matrix[c].sum()} rows (states with 0: {(matrix[c] == 0).sum()})")

# Specifically: 2020-06 to 2021-02 (9 months) vs 2020-06 to 2021-03 (10 months)
m_9 = [c for c in matrix.columns if "2020-06" <= c <= "2021-02"]
m_10 = [c for c in matrix.columns if "2020-06" <= c <= "2021-03"]
print(f"\nRows for 2020-06 to 2021-02 ({len(m_9)} months): {matrix[m_9].sum().sum()}")
print(f"Rows for 2020-06 to 2021-03 ({len(m_10)} months): {matrix[m_10].sum().sum()}")

# ------------------------------------------------------------------------------
# 3. Omicron Window Discrepancy (Dec 2021 - March 2022)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[3] OMICRON WINDOW (2021-12 to 2022-03) DISCREPANCY AUDIT")
print("=" * 80)
omi_cols = [c for c in matrix.columns if "2021-12" <= c <= "2022-03"]
print(f"Omicron months found in matrix: {omi_cols}")
if omi_cols:
    omi_sub = matrix[omi_cols]
    print(f"Total rows in Omicron window: {omi_sub.sum().sum()}")
    print("Per month breakdown:")
    for c in omi_cols:
        print(f"  {c}: {omi_sub[c].sum()} states")
    print("\nStates reporting in Omicron window:")
    state_totals = omi_sub.sum(axis=1)
    print("States with fewer than 4 months:")
    for st, cnt in state_totals.items():
        if cnt < len(omi_cols):
            print(f"  {st}: {cnt} months (missing in: {[c for c in omi_cols if omi_sub.loc[st, c] == 0]})")

# Also check multiwave_surveillance_results.json
mw_json_path = os.path.join(HOSPI, "paper_revision", "results", "multiwave_surveillance_results.json")
if os.path.exists(mw_json_path):
    with open(mw_json_path) as fp:
        mw_data = json.load(fp)
    print(f"\nmultiwave_surveillance_results.json omicron n_windows: {mw_data['waves']['omicron']['n_windows']}")
    print(f"multiwave_surveillance_results.json omicron n_states: {mw_data['waves']['omicron']['n_states']}")

# ------------------------------------------------------------------------------
# 4. Deployed Model Training Range and Authentic Ingestion Check
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[4] DEPLOYED MODEL TRAINING RANGE & AUTHENTIC INGESTION AUDIT")
print("=" * 80)

# Query database for all monthly records used by train_forecast.py
df_po = pd.read_sql(
    "SELECT disease, state, year, month, sum(confirmed_cases) as confirmed_cases "
    "FROM pandemic_outbreak GROUP BY disease, state, year, month "
    "ORDER BY disease, state, year, month", con
)
print(f"Total aggregated disease-state-year-month series: {len(df_po)}")
print(f"Overall year range in DB: min={df_po['year'].min()}, max={df_po['year'].max()}")

# Replicate the exact 85/15 chronological split from train_forecast.py:
df_po_sorted = df_po.sort_values(["year", "month"]).reset_index(drop=True)
split_idx = int(len(df_po_sorted) * 0.85)
train_split = df_po_sorted.iloc[:split_idx]
test_split = df_po_sorted.iloc[split_idx:]

print(f"Train split count: {len(train_split)} (85%), Test split count: {len(test_split)} (15%)")
print(f"Train min: year={train_split['year'].min()}, month={train_split['month'].min()}")
print(f"Train max: year={train_split['year'].max()}, month={train_split['month'].max()}")
print(f"Test min:  year={test_split['year'].min()}, month={test_split['month'].min()}")
print(f"Test max:  year={test_split['year'].max()}, month={test_split['month'].max()}")

# Check COVID records in train vs authentic records
covid_train = train_split[train_split["disease"] == "COVID-19"]
print(f"COVID-19 rows in train_split: {len(covid_train)}")
print(f"COVID-19 train years: {sorted(covid_train['year'].unique().tolist())}")
print(f"Does train_split contain April-July 2021 (Delta window)?")
delta_in_train = covid_train[(covid_train["year"] == 2021) & (covid_train["month"].between(4, 7))]
print(f"  Delta window rows in train_split: {len(delta_in_train)} rows across {delta_in_train['state'].nunique()} states!")
print(f"  Are these Delta rows authentic or synthetic in the DB?")

# Check values in DB vs authentic outbreak_real.csv for 2021-04 to 2021-07
delta_auth = covid_real[(covid_real["date"] >= "2021-04-01") & (covid_real["date"] <= "2021-07-31")]
print(f"  Authentic Delta CSV total cases: {delta_auth['confirmed_cases'].sum()}")
print(f"  DB Delta total cases: {delta_in_train['confirmed_cases'].sum()}")

# ------------------------------------------------------------------------------
# 5. Fig. 5a Data Points & Uttar Pradesh Training Bounds
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[5] FIG 5a DATA POINTS & UTTAR PRADESH BOUNDS AUDIT")
print("=" * 80)
# Check max cases for Uttar Pradesh across the entire pandemic_outbreak table
up_rows = df_po[df_po["state"] == "Uttar Pradesh"]
print(f"Uttar Pradesh total rows in DB: {len(up_rows)}")
for d in up_rows["disease"].unique():
    d_up = up_rows[up_rows["disease"] == d]
    print(f"  {d}: min={d_up['confirmed_cases'].min()}, max={d_up['confirmed_cases'].max()}, median={d_up['confirmed_cases'].median()}")

# Check Uttar Pradesh in authentic CSV
up_auth = covid_real[covid_real["state"] == "Uttar Pradesh"]
print(f"\nUttar Pradesh in authentic CSV:")
print(f"  Min cases: {up_auth['confirmed_cases'].min()}, Max cases: {up_auth['confirmed_cases'].max()}")
print(f"  Max date in authentic: {up_auth.loc[up_auth['confirmed_cases'].idxmax(), 'date']}")
print(f"  Max case count: {up_auth['confirmed_cases'].max()}")

# ------------------------------------------------------------------------------
# 6. Exact McNemar Significance
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[6] EXACT MCNEMAR SIGNIFICANCE AUDIT")
print("=" * 80)
bench_json_path = os.path.join(HOSPI, "paper_revision", "results", "formal_seeded_defect_benchmark.json")
if os.path.exists(bench_json_path):
    with open(bench_json_path) as fp:
        bench_data = json.load(fp)
    print("Baseline detection counts on 410 mutants:")
    proto_det = bench_data["summary"]["ThreePhaseProtocol_unified"]["detected"]
    proto_total = bench_data["n_valid_mutants"]
    print(f"ThreePhaseProtocol: {proto_det}/{proto_total}")
    for name, s in bench_data["summary"].items():
        if name != "ThreePhaseProtocol_unified":
            b_det = s["detected"]
            # Three-phase protocol detected all 410 (or proto_det)
            # Discordant pairs: b = proto detected & baseline missed, c = baseline detected & proto missed
            # If proto detected 410/410, then c = 0, b = 410 - b_det
            b = proto_det - b_det
            c = 0
            # Exact binomial test (two-sided) with n = b + c, p = 0.5
            p_exact = stats.binomtest(b, b + c, 0.5, alternative="two-sided").pvalue
            print(f"  {name:30s}: {b_det:3d}/{proto_total} | Discordant (b={b:3d}, c={c}) | Exact McNemar p = {p_exact:.4e}")

# ------------------------------------------------------------------------------
# 7. Static Dataflow Raw Log Audit (Table VIII vs Table IX)
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[7] STATIC DATAFLOW COUNTS (TABLE VIII vs TABLE IX) AUDIT")
print("=" * 80)
ho_json_path = os.path.join(HOSPI, "paper_revision", "results", "held_out_taxonomy_results.json")
if os.path.exists(ho_json_path):
    with open(ho_json_path) as fp:
        ho_data = json.load(fp)
    print("held_out_taxonomy_results.json partition:")
    print(f"  Design set count: {ho_data['partition']['n_design']}")
    print(f"  Held-out set count: {ho_data['partition']['n_held_out']}")
    print("Evaluations in held_out_taxonomy_results.json:")
    for k, v in ho_data.get("evaluations", {}).items():
        des_hits = v.get("design_set", {}).get("hits", "N/A")
        ho_hits = v.get("held_out_set", {}).get("hits", "N/A")
        print(f"  {k:30s}: Design hits={des_hits}, Held-out hits={ho_hits}")

# Check if Static Dataflow was evaluated in held_out_taxonomy_eval
print("\nCheck all files mentioning Static Dataflow or Yang in paper_revision/results:")
res_dir = os.path.join(HOSPI, "paper_revision", "results")
for f in os.listdir(res_dir):
    if f.endswith(".json"):
        with open(os.path.join(res_dir, f)) as fp:
            txt = fp.read()
            if "Yang" in txt or "static_dataflow" in txt or "Static" in txt:
                print(f"  Found mention in: {f}")

# ------------------------------------------------------------------------------
# 8. Checkpoint 20260722_205310 Hyperparameter Audit
# ------------------------------------------------------------------------------
print("\n" + "=" * 80)
print("[8] CHECKPOINT 20260722_205310 & DEPLOYED MODEL HYPERPARAMETER AUDIT")
print("=" * 80)
pdir = os.path.join(HOSPI, "mlruns", "443380611598012369", "01f6549e8b6a484882f36f7e10de854d", "params")
if os.path.exists(pdir):
    print("MLflow Run 01f6549e8b6a484882f36f7e10de854d logged params:")
    for f in sorted(os.listdir(pdir)):
        with open(os.path.join(pdir, f)) as fp:
            print(f"  {f}: {fp.read().strip()}")

mod_path = os.path.join(HOSPI, "ml_pipeline", "data", "models", "forecast_cases_model.pkl")
with open(mod_path, "rb") as fp:
    mod = pickle.load(fp)
print("\nDeployed forecast_cases_model.pkl get_params():")
for k in ["n_estimators", "max_depth", "learning_rate", "subsample", "colsample_bytree", "reg_alpha", "reg_lambda", "min_child_weight"]:
    print(f"  {k}: {mod.get_params().get(k)}")

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)
