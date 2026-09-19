# HELD-OUT TAXONOMY EVALUATION PROTOCOL v1.0
**Pre-Registration Document for Out-of-Distribution Generalization & Adversarial Evaluation**

Committed on branch udit-revision **before running any detector on any held-out mutant or adversarial evasion case**.

---

## 1. Ground Rules & Independence Principles

1. **Zero Post-Hoc Tuning**: Detectors, thresholds (tau_AR = 0.50, tau_AST = 0.0, tau_TEFV = 0.0), and baseline configurations are frozen at this commit prior to running held-out evaluation.
2. **Unvarnished Reporting**: All outcomes—including misses, generalization drops, and successful adversarial evasions—will be reported transparently with root-cause diagnoses.
3. **No Fabricated Targets**: No numeric detection target ranges (e.g. 50%-85%) are pre-committed to prevent subconscious pressure during test construction. Raw empirical rates will speak for themselves.
4. **Leakage Prevention**: All evaluation waves must strictly post-date the training window. Wave-1 is excluded from forecaster evaluation because it was used during model training.

---

## 2. Held-Out Taxonomy Partition (Master Seed = 42)

The 9 mutation operators (M1 through M9) are partitioned into a **Design Set** (~55.6%, 5 operators) and a **Held-Out Set** (~44.4%, 4 operators) using Python's standard 
andom.Random(42) on the canonical operator list:

`python
import random
ops = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7', 'M8', 'M9']
rng = random.Random(42)
shuffled = ops.copy()
rng.shuffle(shuffled)
# Resulting order: ['M4', 'M7', 'M8', 'M5', 'M9', 'M3', 'M6', 'M1', 'M2']
design_set   = sorted(shuffled[:5])  # ['M4', 'M5', 'M7', 'M8', 'M9']
held_out_set = sorted(shuffled[5:])  # ['M1', 'M2', 'M3', 'M6']
`

### Partition Composition

| Set | Operator | Defect Description | Target Audit Phase |
|---|---|---|---|
| **Design** | M4 | Temporal order shuffled before train/test split | Phase 2 (AST-TIV) |
| **Design** | M5 | Artifact/inference feature-count mismatch | Phase 3 (DTEFV) |
| **Design** | M7 | Silent fallback on exception returns constant | Phase 3 (DTEFV) |
| **Design** | M8 | Input ignored at inference / constant fed | Phase 3 (DTEFV) |
| **Design** | M9 | Monitoring route unmounted / 404 response | Phase 2 / Phase 3 |
| **Held-Out** | M1 | Synthetic tail appended to real-tagged records | Phase 1 (PSAP) |
| **Held-Out | M2 | Deterministic target formula reconstruction | Phase 2 (AST-TIV) |
| **Held-Out** | M3 | Contemporaneous leakage / same-period aggregate | Phase 2 (AST-TIV) |
| **Held-Out** | M6 | Metadata type corrupted / loading crash | Phase 3 (DTEFV) |

### Out-of-Phase Generalization Properties
Because no phase stratification was applied, **Phase 1 (M1) is entirely held out**, while **Phase 2 formula reconstruction (M2) and contemporaneous leakage (M3)** are also held out. The design set is dominated by runtime/interface mismatches (Phase 3). This creates a rigorous test of whether detectors generalize across architectural phases without being tuned on those specific archetypes.

---

## 3. Hypotheses & Statistical Evaluation Plan

1. **H1 (Generalization Recall)**: Protocol recall on the Held-Out Set is measured with Wilson 95% confidence intervals and compared directly against the Design Set.
2. **H2 (Adversarial Evasion)**: Adversarial evasion test cases are engineered to exploit structural detector limitations (cross-module boundaries, feature collinearity dilution, intermediate lookup joins, rare input triggers). The protocol reports both hits and evasions, accompanied by a root-cause taxonomy.
3. **H3 (Rater Independence)**: Mutants authored by independent raters given only abstract taxonomy definitions will be tested to measure semantic transfer across independent implementations.
4. **H4 (Multi-Wave Invariance)**: Out-of-sample forecaster evaluation on Delta (Wave 2) and Omicron (Wave 3) will be evaluated using cluster-robust Diebold-Mariano, paired Wilcoxon, and TOST equivalence tests, controlling Family-Wise Error Rate (FWER) via Holm-Bonferroni correction.
