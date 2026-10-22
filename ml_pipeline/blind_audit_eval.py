"""
Expanded Blind Audit Benchmark Evaluation (N = 32 targets)
Two Independent Evaluators:
- Rater 1: ML Systems / Research Engineer
- Rater 2: Production MLOps / Software Reliability Engineer

Evaluates 18 Defect Targets and 14 Clean Controls across four platforms:
1. HospitalIQ (Pandemic multi-model surveillance system)
2. HAIRLAB / Yan et al. (Nature Machine Intelligence 2020 clinical mortality model)
3. Youyang Gu SEIR Simulator (CDC COVID-19 Forecast Hub ensemble)
4. Shamout et al. (npj Digital Medicine 2021 multi-modal clinical deterioration)
Alongside clean classical baselines (ARIMA, differenced GBR).
"""

import math

def wilson_ci(k, n, z=1.95996):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1.0 + (z**2) / n
    center = (p + (z**2) / (2 * n)) / denom
    margin = (z / denom) * math.sqrt((p * (1 - p) / n) + (z**2) / (4 * n**2))
    return (max(0.0, center - margin) * 100, min(1.0, center + margin) * 100)

def cohen_kappa(rater1, rater2):
    assert len(rater1) == len(rater2)
    n = len(rater1)
    categories = sorted(list(set(rater1 + rater2)))
    
    # Observed agreement
    po = sum(1 for r1, r2 in zip(rater1, rater2) if r1 == r2) / n
    
    # Expected agreement
    pe = 0.0
    for cat in categories:
        p1 = sum(1 for r in rater1 if r == cat) / n
        p2 = sum(1 for r in rater2 if r == cat) / n
        pe += p1 * p2
        
    if pe == 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)

def main():
    # 32 Benchmark Targets: (Target Name, Ground Truth, Rater 1 Binary, Rater 2 Binary, Rater 1 Taxonomy, Rater 2 Taxonomy)
    # Taxonomy categories: FormulaRecon, AR1Dominance, NegativeSkill, GenuineClean, RuntimeCrash, DegenerateInput, TemporalLeakage, ProvenanceContam
    benchmarks = [
        # --- HospitalIQ Targets (11 Defects, 3 Clean) ---
        ('HospitalIQ: COVID-19 synthetic endemic tail labeled real', 'DEFECT', 'DEFECT', 'DEFECT', 'ProvenanceContam', 'ProvenanceContam'),
        ('HospitalIQ: H5N1 Africa-labeled records in Indian surveillance', 'DEFECT', 'DEFECT', 'DEFECT', 'ProvenanceContam', 'ProvenanceContam'),
        ('HospitalIQ: R0 formula reconstruction from synthetic rules', 'DEFECT', 'DEFECT', 'DEFECT', 'FormulaRecon', 'FormulaRecon'),
        ('HospitalIQ: PatientRisk formula reconstruction from triage rule', 'DEFECT', 'DEFECT', 'DEFECT', 'FormulaRecon', 'FormulaRecon'),
        ('HospitalIQ: Lockdown formula reconstruction from CFR/R0 formula', 'DEFECT', 'DEFECT', 'DEFECT', 'FormulaRecon', 'FormulaRecon'),
        ('HospitalIQ: Forecast AR(1) persistence dominance (lag-1 55%)', 'DEFECT', 'DEFECT', 'CLEAN', 'AR1Dominance', 'GenuineClean'),
        ('HospitalIQ: Bed capacity regressor negative skill (R2 < 0)', 'DEFECT', 'DEFECT', 'DEFECT', 'NegativeSkill', 'NegativeSkill'),
        ('HospitalIQ: Scenario training leakage of same-year CFR/R0 actuals', 'DEFECT', 'DEFECT', 'DEFECT', 'TemporalLeakage', 'TemporalLeakage'),
        ('HospitalIQ: R0 predictor AttributeError on scalar metadata .get()', 'DEFECT', 'DEFECT', 'DEFECT', 'RuntimeCrash', 'RuntimeCrash'),
        ('HospitalIQ: Hospital predictor ValueError (5 vs 8 features)', 'DEFECT', 'DEFECT', 'DEFECT', 'RuntimeCrash', 'RuntimeCrash'),
        ('HospitalIQ: Mortality population-invariance under degenerate inputs', 'DEFECT', 'DEFECT', 'DEFECT', 'DegenerateInput', 'NegativeSkill'),
        ('HospitalIQ: Authenticated March 2020-July 2021 surveillance', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('HospitalIQ: Summary refresh service clean DB aggregation', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('HospitalIQ: Regional bed distribution deterministic query path', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        
        # --- Yan et al. Targets (3 Defects, 2 Clean) ---
        ('Yan et al.: Terminal horizon selection via .groupby().last()', 'DEFECT', 'DEFECT', 'DEFECT', 'TemporalLeakage', 'TemporalLeakage'),
        ('Yan et al.: Missing hs-CRP defaults to death probability 0.755', 'DEFECT', 'DEFECT', 'DEFECT', 'DegenerateInput', 'DegenerateInput'),
        ('Yan et al.: Negative biomarker inputs silently accepted', 'DEFECT', 'DEFECT', 'DEFECT', 'DegenerateInput', 'DegenerateInput'),
        ('Yan et al.: Admission Day 0 non-leaked patient trajectory', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('Yan et al.: Valid physiological vital vector forward inference', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),

        # --- Youyang Gu SEIR Targets (2 Defects, 3 Clean) ---
        ('YYG-SEIR: Inverted horizon T_start > T_end silent execution', 'DEFECT', 'DEFECT', 'DEFECT', 'RuntimeCrash', 'RuntimeCrash'),
        ('YYG-SEIR: Negative transmission rate parameter accepted', 'DEFECT', 'DEFECT', 'DEFECT', 'DegenerateInput', 'DegenerateInput'),
        ('YYG-SEIR: US National calibrated simulation (March-June 2020)', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('YYG-SEIR: California state-level compartmental projection', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('YYG-SEIR: Valid epidemiological bounds verification', 'CLEAN', 'CLEAN', 'DEFECT', 'GenuineClean', 'DegenerateInput'),

        # --- Shamout et al. Targets (2 Defects, 3 Clean) ---
        ('Shamout: Negative respiration rate unmapped silent pass', 'DEFECT', 'DEFECT', 'DEFECT', 'DegenerateInput', 'DegenerateInput'),
        ('Shamout: GMIC tensor dimension mismatch (1,3,512,512)', 'DEFECT', 'DEFECT', 'DEFECT', 'RuntimeCrash', 'RuntimeCrash'),
        ('Shamout: COVID-GMIC clean 1024x1024 CXR forward pass', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('Shamout: COVID-GBM tabular clean feature inference', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('Shamout: COVID-DRC discrete-time survival curve generation', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),

        # --- Independent Baselines & CHIME (3 Clean) ---
        ('Clean Baseline 1: First-differenced incident case GBR', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('Clean Baseline 2: Box-Jenkins ARIMA with stationary differencing', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
        ('Penn CHIME: Baseline Pennsylvania regional catchment simulation', 'CLEAN', 'CLEAN', 'CLEAN', 'GenuineClean', 'GenuineClean'),
    ]

    total = len(benchmarks)
    n_defects = sum(1 for b in benchmarks if b[1] == 'DEFECT')
    n_clean = sum(1 for b in benchmarks if b[1] == 'CLEAN')
    
    print(f"=== Benchmark Suite Overview (N = {total}) ===")
    print(f"Total Targets: {total} (Defects: {n_defects}, Clean Controls: {n_clean})")
    
    for rater_idx, rater_name in [(2, 'Rater 1 (ML Systems Engineer)'), (3, 'Rater 2 (Production MLOps Engineer)')]:
        tp = sum(1 for b in benchmarks if b[1] == 'DEFECT' and b[rater_idx] == 'DEFECT')
        tn = sum(1 for b in benchmarks if b[1] == 'CLEAN' and b[rater_idx] == 'CLEAN')
        fp = sum(1 for b in benchmarks if b[1] == 'CLEAN' and b[rater_idx] == 'DEFECT')
        fn = sum(1 for b in benchmarks if b[1] == 'DEFECT' and b[rater_idx] == 'CLEAN')

        sens, sens_ci = (tp / (tp + fn)) * 100, wilson_ci(tp, tp + fn)
        spec, spec_ci = (tn / (tn + fp)) * 100, wilson_ci(tn, tn + fp)
        acc, acc_ci = ((tp + tn) / total) * 100, wilson_ci(tp + tn, total)

        print(f"\n--- {rater_name} vs. Ground Truth ---")
        print(f"TP: {tp}, TN: {tn}, FP: {fp}, FN: {fn}")
        print(f"Sensitivity: {sens:.1f}% (95% Wilson CI: [{sens_ci[0]:.1f}%, {sens_ci[1]:.1f}%])")
        print(f"Specificity: {spec:.1f}% (95% Wilson CI: [{spec_ci[0]:.1f}%, {spec_ci[1]:.1f}%])")
        print(f"Accuracy:    {acc:.1f}% (95% Wilson CI: [{acc_ci[0]:.1f}%, {acc_ci[1]:.1f}%])")

    # Inter-rater Agreement (Rater 1 vs. Rater 2)
    binary_r1 = [b[2] for b in benchmarks]
    binary_r2 = [b[3] for b in benchmarks]
    binary_kappa = cohen_kappa(binary_r1, binary_r2)
    binary_raw = sum(1 for r1, r2 in zip(binary_r1, binary_r2) if r1 == r2) / total * 100

    tax_r1 = [b[4] for b in benchmarks]
    tax_r2 = [b[5] for b in benchmarks]
    tax_kappa = cohen_kappa(tax_r1, tax_r2)
    tax_raw = sum(1 for r1, r2 in zip(tax_r1, tax_r2) if r1 == r2) / total * 100

    print("\n=== Inter-Rater Agreement (Rater 1 vs. Rater 2) ===")
    print(f"Binary Defect Detection: Raw Agreement = {binary_raw:.1f}%, Cohen's kappa = {binary_kappa:.3f}")
    print(f"Taxonomy Classification: Raw Agreement = {tax_raw:.1f}%, Cohen's kappa = {tax_kappa:.3f}")

if __name__ == '__main__':
    main()