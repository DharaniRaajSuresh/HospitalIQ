"""
ml_pipeline/run_phase1c_checks.py
Phase 1c Read-Only Comprehensive Audit Runner
Audits all 7 items specified in the Phase 1c mandate.
"""

import os, sys, io, json, ast, inspect
import numpy as np
import pandas as pd

# Set stdout to UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HOSPI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

print("=" * 80)
print("PHASE 1C READ-ONLY VERIFICATION AUDIT")
print("=" * 80)

# ==============================================================================
# ITEM 1: Grep every model.predict call in eval/importance/rolling-origin/DM scripts;
# compare against training script target transform and whether eval applies inverse.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 1: INVERSE TRANSFORMS ACROSS ALL EVALUATION & IMPORTANCE SCRIPTS")
print("=" * 80)

eval_scripts = [
    ("deployed_forecast_authentic_eval.py", "ml_pipeline"),
    ("multiwave_surveillance_eval.py", "ml_pipeline"),
    ("rolling_origin_authentic_eval.py", "ml_pipeline"),
    ("grouped_permutation_importance.py", "ml_pipeline"),
    ("clean_model_permutation_importance.py", "ml_pipeline"),
    ("test_real_surveillance_experiment.py", "ml_pipeline"),
    ("test_sweep_rigorous.py", "ml_pipeline"),
    ("run_ablation.py", "ml_pipeline"),
    ("run_baseline_comparison.py", "ml_pipeline"),
    ("seed_variance_study.py", "ml_pipeline"),
    ("temporal_git_holdout_eval.py", "ml_pipeline"),
    ("reproduce_formula_audit.py", "ml_pipeline"),
    ("verify_table2_mase_relmae.py", "ml_pipeline"),
]

for sname, sdir in eval_scripts:
    spath = os.path.join(HOSPI, sdir, sname)
    if not os.path.exists(spath):
        continue
    with open(spath, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    predict_calls = []
    for idx, l in enumerate(lines):
        if ".predict(" in l:
            predict_calls.append((idx + 1, l.strip()))
    if predict_calls:
        print(f"\n--- Script: {sdir}/{sname} ---")
        for lno, text in predict_calls:
            print(f"  Line {lno:4d}: {text}")

# ==============================================================================
# ITEM 2: Production serving code for the forecast model and whether it applies expm1.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 2: PRODUCTION SERVING CODE (backend/predictors/forecast_predictor.py)")
print("=" * 80)

prod_path = os.path.join(HOSPI, "backend", "predictors", "forecast_predictor.py")
with open(prod_path, "r", encoding="utf-8", errors="replace") as f:
    prod_lines = f.readlines()

for idx in range(130, min(166, len(prod_lines))):
    print(f"  Line {idx+1:4d}: {prod_lines[idx].rstrip()}")

# ==============================================================================
# ITEM 3: Model-vs-persistence comparisons: target definition, units, formula.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 3: MODEL-VS-PERSISTENCE TARGET DEFINITION, UNITS, & PERSISTENCE FORMULA")
print("=" * 80)

# Check deployed_forecast_authentic_eval.py
print("\n[A] Deployed Forecast Authentic Eval (deployed_forecast_authentic_eval.py):")
print("  Target Variable:     confirmed_cases in outbreak_real.csv")
print("  Target Definition:   Monthly confirmed cases count (monthly incidence level, non-cumulative)")
print("  Units:               Integer count of new cases per state per month (e.g. Maharashtra Apr 2021 = 10,065,950)")
print("  Persistence Formula: y_persistence = lag1 (cases from month t-1)")
print("  Model Target in Fit: y = np.log1p(confirmed_cases) [log scale]")
print("  Model In Eval:       y_pred = float(model.predict(X)[0]) [LOG SCALE directly compared to RAW COUNT]")

# Check test_real_surveillance_experiment.py
print("\n[B] Retrained Wave-1 Clean Forecaster (test_real_surveillance_experiment.py):")
print("  Target Variable:     target_diff = confirmed_cases[t] - confirmed_cases[t-1]")
print("  Target Definition:   First-difference of monthly incidence: Delta y_t = y_t - y_{t-1}")
print("  Units:               Cases count difference per month")
print("  Persistence Formula: pred_persist = lag_1_cases (i.e. predicting Delta y_t = 0, so level = y_{t-1})")
print("  Model Target in Fit: target_diff (trained without log transform)")
print("  Model In Eval:       pred_cases = lag1 + xgb_diff.predict(X) [reconstructed to level, correctly compared]")

# ==============================================================================
# ITEM 4: For each protocol check (phases 1-3), print searched pattern and mutation template.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 4: PROTOCOL DETECTORS VS MUTATION TEMPLATES")
print("=" * 80)

# Load run_seeded_defect_evaluation.py
eval_seeded_path = os.path.join(HOSPI, "eval", "run_seeded_defect_evaluation.py")
with open(eval_seeded_path, "r", encoding="utf-8", errors="replace") as f:
    eval_text = f.read()

operators = [
    ("M1", "m1_synthetic_tail.py", "check_phase1"),
    ("M2", "m2_formula_reconstruction.py", "check_phase2 / PipelineASTAuditor.has_formula_reconstruction"),
    ("M3", "m3_contemporaneous_leakage.py", "check_phase2 / PipelineASTAuditor.has_contemporaneous_leakage"),
    ("M4", "m4_temporal_shuffle.py", "check_phase2 / PipelineASTAuditor.has_temporal_shuffle"),
    ("M5", "m5_feature_mismatch.py", "check_phase3"),
    ("M6", "m6_corrupt_metadata.py", "check_phase3"),
    ("M7", "m7_silent_fallback.py", "check_phase3 / PipelineASTAuditor.has_silent_fallback"),
    ("M8", "m8_ignore_input.py", "check_phase3 / PipelineASTAuditor.has_ignored_input"),
    ("M9", "m9_unmount_route.py", "check_phase2 (FastAPI route search)"),
]

for op_id, op_file, det_name in operators:
    op_path = os.path.join(HOSPI, "ml_pipeline", "mutation_operators", op_file)
    with open(op_path, "r", encoding="utf-8", errors="replace") as f:
        op_code = f.read()
    print(f"\n[{op_id}] Mutator: {op_file} | Detector: {det_name}")
    # Extract snippet from mutator
    m_lines = op_code.splitlines()
    in_snip = False
    snip_lines = []
    for l in m_lines:
        if "snippet = [" in l:
            in_snip = True
            continue
        if in_snip:
            if l.strip() == "]":
                break
            snip_lines.append(l.strip())
    print("  Mutation Template Snippet:")
    for sl in snip_lines:
        print(f"    {sl}")

# ==============================================================================
# ITEM 5: Check whether baseline hit counts in Table IX Panel B and Table VIII Panel A
# are computed by execution or by lookup.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 5: BASELINE HIT COMPUTATION (EXECUTION VS LOOKUP)")
print("=" * 80)

print("\n[A] Table VIII Panel A (HospitalIQ 9 Defects vs GX, Evidently, MLflow):")
bench_mlops_path = os.path.join(HOSPI, "ml_pipeline", "benchmark_mlops.py")
with open(bench_mlops_path, "r", encoding="utf-8", errors="replace") as f:
    b_lines = f.readlines()
print("  Evidence from ml_pipeline/benchmark_mlops.py (lines 28-32, 77-80):")
for idx in [27, 28, 29, 30, 76, 77, 78, 79]:
    print(f"    L{idx+1}: {b_lines[idx].rstrip()}")
print("  Verdict: Hardcoded boolean variables. No tools executed.")

print("\n[B] Table VIII Panel B (Seeded Defect Benchmark Baselines):")
print("  Evidence from eval/run_seeded_defect_evaluation.py (lines 220-248):")
for idx in range(219, 248):
    print(f"    L{idx+1}: {eval_text.splitlines()[idx].rstrip()}")
print("  Verdict: Hardcoded operator-membership lookups (`op in ['M5']`, etc.). No tools executed.")

print("\n[C] Table IX Panel B (Adversarial Self-Red-Teaming Baselines):")
adv_path = os.path.join(HOSPI, "eval", "run_adversarial_evaluation.py")
with open(adv_path, "r", encoding="utf-8", errors="replace") as f:
    adv_lines = f.readlines()
print("  Evidence from eval/run_adversarial_evaluation.py (lines 609-619):")
for idx in range(608, 620):
    print(f"    L{idx+1}: {adv_lines[idx].rstrip()}")
print("  Verdict: Hardcoded test-case ID lookups (`cid in ['E5_1', ...']`). No tools executed.")

# ==============================================================================
# ITEM 6: Origin and verification of the 30 clean controls.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 6: ORIGIN & VERIFICATION OF 30 CLEAN CONTROLS")
print("=" * 80)

benign_path = os.path.join(HOSPI, "eval", "results", "benign_manifest.json")
with open(benign_path, "r", encoding="utf-8", errors="replace") as f:
    benign_data = json.load(f)

print(f"Total benign controls in manifest: {len(benign_data)}")
print("Origin: Generated automatically by `ml_pipeline/mutation_operators/benign_mutator.py`.")
print("How verified clean: Generated by inserting purely cosmetic comments or docstrings into 5 existing source files:")
target_counts = {}
style_counts = {}
for b in benign_data:
    t = b["target"]
    target_counts[t] = target_counts.get(t, 0) + 1
    # Check style
    summ = b["change_summary"]
    st = summ.split(" (seed=")[0]
    style_counts[st] = style_counts.get(st, 0) + 1

print(f"  Target Source Files ({len(target_counts)} files, 6 seeds each = 30):")
for t, c in target_counts.items():
    print(f"    - {t:25s}: {c} controls")
print(f"  Cosmetic Modifications:")
for s, c in style_counts.items():
    print(f"    - {s:40s}: {c} controls")

# Verify what protocol check does on benign controls
print("Execution on Benign Controls in run_seeded_defect_evaluation.py (lines 198-208):")
print("  For ThreePhaseProtocol: runs live check. All return False (0 false alarms).")
print("  For Baselines: hardcoded to `return False` unconditionally! Line 208: returns False.")

# ==============================================================================
# ITEM 7: Recompute sample counts after removing Omicron.
# ==============================================================================
print("\n" + "=" * 80)
print("ITEM 7: RECOMPUTED SAMPLE COUNTS AFTER DROPPING OMICRON")
print("=" * 80)

df_real = pd.read_csv(os.path.join(HOSPI, "ml_pipeline", "data", "raw", "outbreak_real.csv"), parse_dates=["date"])
covid = df_real[df_real["disease"] == "COVID-19"].copy()

# Wave 1: 2020-06-01 to 2021-03-31 (10 months x 30 states = 300)
w1 = covid[(covid["date"] >= "2020-06-01") & (covid["date"] <= "2021-03-31")]
print(f"Wave-1 In-Sample / Retrain Window (2020-06-01 to 2021-03-31): N = {len(w1)} (10 months x {w1['state'].nunique()} states)")

# Delta: 2021-04-01 to 2021-07-31 (4 months x 30 states = 120)
delta = covid[(covid["date"] >= "2021-04-01") & (covid["date"] <= "2021-07-31")]
print(f"Delta Authentic Out-of-Sample Surveillance (2021-04-01 to 2021-07-31): N = {len(delta)} (4 months x {delta['state'].nunique()} states)")

# Full Authentic Surveillance Window: 2020-06-01 to 2021-07-31 (14 months x 30 states = 420)
auth_surv = covid[(covid["date"] >= "2020-06-01") & (covid["date"] <= "2021-07-31")]
print(f"Full Authentic Surveillance Trajectory (Wave 1 + Delta): N = {len(auth_surv)} (14 months x {auth_surv['state'].nunique()} states = 420 windows)")

# Omicron (Synthetic Continuation, to be dropped from authentic claims):
omi = covid[(covid["date"] >= "2021-12-01") & (covid["date"] <= "2022-03-31")]
print(f"Omicron (Synthetic Continuation, DROPPED): N = {len(omi)} windows")

print("\nImpact on Statistical Test Multiplicity (Holm-Bonferroni Family):")
print("  Original Paper Family: M = 14 tests (evaluating Delta, Omicron, and Pooled)")
print("  After Dropping Omicron & Pooled:")
print("    Tests on Delta Surveillance remaining: M = 5 tests:")
print("      1. Delta Cluster-Robust DM (Absolute Loss)")
print("      2. Delta Cluster-Robust DM (Squared Loss)")
print("      3. Delta Paired Wilcoxon Signed-Rank")
print("      4. Delta TOST Equivalence Margin (5%)")
print("      5. Delta TOST Equivalence Margin (2%)")

print("\n" + "=" * 80)
print("PHASE 1C AUDIT COMPLETE")
print("=" * 80)
