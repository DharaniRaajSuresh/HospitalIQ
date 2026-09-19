# EVALUATION PROTOCOL v1.0
**Pre-registration document for the seeded-defect benchmark.**
Committed and tagged (eval-freeze-v1) on the udit-revision branch **before any detector
was run on any mutant**. After this tag, operators, seeds, thresholds, and tool configurations
are frozen. Bug fixes are permitted in new commits with documented reasons; re-runs must cover
all mutants, not just the failing ones.

---

## 0. Purpose and Ground Rules

This document pre-specifies every design choice for the seeded-defect evaluation described in
Step 2 of the 8-step reviewer revision plan. Adherence to these ground rules is what makes
the evaluation independent of result tuning:

1. **Nothing is tuned after seeing results.** Operators, seeds, thresholds, and baseline
   configs below are frozen at this commit.
2. **Report whatever comes out**, including misses, low recall, and unfavorable results.
3. **If a result contradicts a paper claim, change the paper claim, not the protocol.**

---

## 1. Research Hypotheses

| ID | Hypothesis | Decision threshold |
|----|-----------|-------------------|
| H1 | PSAP+DTEFV combined recall >= 0.75 across applicable mutants | Wilson 95% CI lower >= 0.50 |
| H2 | Phase 2 recall >= 0.75 on M2, M3, M4 | Wilson 95% CI lower >= 0.40 |
| H3 | Phase 3 recall >= 0.75 on M5, M6, M7, M8 | Wilson 95% CI lower >= 0.40 |
| H4 | False-alarm rate on benign mutants < 0.10 | Wilson 95% CI upper <= 0.20 |
| H5 | Protocol recall >= 0.50 where each baseline tool < 0.25 | Qualitative |

---

## 2. Mutation Operators (M1-M9)

M1: Synthetic tail appended to real-tagged records (Phase 1)
M2: Target reconstructible from inputs / formula reconstruction (Phase 2)
M3: Contemporaneous leakage - same-period aggregate as feature (Phase 2)
M4: Temporal order shuffled before train/test split (Phase 2)
M5: Artifact/inference feature-count mismatch (Phase 3)
M6: Metadata type corrupted - loading raises TypeError (Phase 3)
M7: Silent fallback on exception - returns constant (Phase 3)
M8: Input ignored at inference - feature replaced with constant (Phase 3)
M9: Monitoring route unmounted - GET /audit returns 404 (Phase 2/3)

Full specs: see mutation_operators/ directory.

---

## 3. Target Selection

Included: Yan et al., Yu-Group, Wisconsin Classifier, Empirical Forecaster,
Resource Demand Regressor, HospitalIQ commit c699115.

Excluded from artifact mutation: Penn CHIME (mechanistic ODE), Youyang Gu SEIR
(mechanistic), MIMIC-IV ICU mortality SQL library, Shamout et al. private weights.

---

## 4. Sample Size

- Minimum 10 valid mutants per operator (90-120 total)
- >= 30 benign semantics-preserving control mutants
- All 6 unmodified targets as negative controls

---

## 5. Seeds (FIXED, DO NOT CHANGE)

MASTER_SEED = 42
Mutant seeds derived from np.random.RandomState(42).randint(0, 10000, size=200)

M1: [6295, 8416, 5696, 5765, 5419, 6697, 6827, 2505, 3271, 1491]
M2: [5705, 6851, 7420, 4037, 4265, 1618, 4578, 7248, 4978, 5338]
M3: [5683, 1285, 2009, 5545, 5817, 4563, 8558, 1477, 7046, 9645]
M4: [6399, 9791, 7437, 1780, 7494, 3877, 9534, 1481, 4895, 9380]
M5: [8890, 1748, 1879, 8161, 5754, 1023, 6779, 3620, 6197, 6453]
M6: [5748, 1823, 4477, 7124, 5673, 4438, 5286, 7736, 8200, 9600]
M7: [2870, 7049, 7573, 1038, 6817, 5851, 3248, 5040, 3478, 4888]
M8: [7820, 1978, 8432, 4295, 8731, 2047, 9302, 3871, 4032, 7241]
M9: [5847, 7253, 9241, 3847, 8274, 1934, 6219, 4821, 3917, 8534]
Benign: [9384, 7645, 2918, 4572, 1836, 8293, 7462, 9183, 4720, 3847,
         2918, 6745, 1847, 9274, 3618, 8472, 5194, 7382, 2947, 8173,
         4829, 7382, 9473, 1847, 6291, 3841, 8472, 5193, 7384, 2915]

---

## 6. Detectors and Configurations

Each detector run in default and expert config. Config files committed in eval/tool_configs/.
Results reported separately per config.

Detectors: Great Expectations, Evidently AI, MLflow, Deepchecks,
           Yang et al. ASE 2022 / LeakageDetector, PSAP+DTEFV (three-phase protocol)

---

## 7. Metrics and Statistical Plan

PRIMARY: Recall per operator (Wilson 95% CI)
SECONDARY: False-alarm rate on benign mutants (Wilson 95% CI)
TESTS: Paired McNemar exact test (two-sided, alpha=0.05, Bonferroni alpha=0.01 for 5 tools)
REPORTING: Recall over all applicable mutants AND over tool's claimed coverage scope.
MISSES: Root cause documented for every missed mutant.

The 9/9, 7/8, and 0/3 headlines will be updated if the seeded-defect study produces
different numbers. No result will be tuned to reproduce existing headlines.

---

## 8. Exclusion Rules

Mutant excluded if: defect does not provably manifest (per manifestation checks in operator specs),
mutation breaks installation rather than producing subtle behavioral defect, or
two mutants for same operator+target differ only in a randomly placed comment.

All exclusions listed in eval/results/exclusion_log.csv.

---

## 9. OSF Registration Text

PASTE INTO OSF.io -> New Project -> Pre-Registration:

Title: Seeded-Defect Benchmark for Provenance-Separated Auditing of Health ML Pipelines

Authors: Dharani Raaj Suresh, Dhivyashree G J, Dr. Parkavi K (VIT Chennai)

Study description:
We conduct a seeded-defect benchmark evaluating recall of a three-phase
provenance-separated auditing protocol (PSAP+DTEFV) against standard MLOps tools
(Great Expectations, Evidently AI, MLflow, Deepchecks, static leakage analyzers).
Nine mutation operators (M1-M9) applied to 6 target systems. >= 10 valid mutants
per operator (90-120 total) and >= 30 benign controls evaluated.

Hypotheses: H1-H5 as in EVALUATION_PROTOCOL.md (committed and tagged eval-freeze-v1
on GitHub: https://github.com/DharaniRaajSuresh/HospitalIQ).

Primary outcome: Recall per operator with Wilson 95% CIs and paired McNemar tests
(Bonferroni alpha=0.01).

Pre-registration date matches git commit timestamp of tag eval-freeze-v1.
