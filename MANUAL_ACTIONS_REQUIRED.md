# Manual Actions Required (Single-Action Checklist for User)

All code, evaluation scripts, statistics, bug fixes, pre-registration documents, and LaTeX manuscript updates have been executed end-to-end autonomously.

Below is the single action requiring external user credentials (OSF account login) which cannot be performed programmatically without your credentials:

---

### Action 1: Post Frozen Pre-Registration to Open Science Framework (OSF)
**Time required:** ~2 minutes

1. Navigate to: [https://osf.io/registries/osf/new](https://osf.io/registries/osf/new)
2. Select **"OSF Preregistration"** template.
3. Title your registration:
   ```text
   Seeded-Defect Benchmark for Provenance-Separated Auditing of Health ML Pipelines
   ```
4. Copy and paste the pre-prepared registration text below into the description field:

```markdown
Title: Seeded-Defect Benchmark for Provenance-Separated Auditing of Health ML Pipelines
Authors: Dharani Raaj Suresh, Dhivyashree G J, Dr. Parkavi K (VIT Chennai)
Target Venue: IEEE Transactions on Software Engineering (TSE)
Repository: https://github.com/DharaniRaajSuresh/HospitalIQ
Git Freeze Tag: eval-freeze-v1

Study Description:
We evaluate a three-phase provenance-separated auditing protocol (PSAP + DTEFV)
against standard industry MLOps tools (Great Expectations, Evidently AI, MLflow,
Deepchecks, and static AST leakage analyzers) using 9 mutation operators (M1–M9)
across health ML pipeline targets.

Hypotheses:
H1: Combined protocol recall >= 0.75 across applicable mutants (Wilson 95% CI lower >= 0.50).
H2: Phase 2 AST checker recall >= 0.75 on M2, M3, M4 (Wilson 95% CI lower >= 0.40).
H3: Phase 3 execution probe recall >= 0.75 on M5, M6, M7, M8 (Wilson 95% CI lower >= 0.40).
H4: False-alarm rate on benign control mutants < 0.10 (Wilson 95% CI upper <= 0.20).
H5: Protocol achieves recall >= 0.50 on all operator classes where each baseline tool achieves < 0.25.

Frozen Protocol & Code Artifacts:
All operators, random seeds, manifestation criteria, and baseline configurations
are permanently committed to git and tagged at `eval-freeze-v1` in `EVALUATION_PROTOCOL.md`.
```

5. Click **"Review"** and **"Make Registration Public"** (or generate an anonymous view-only link for peer review).

---

### Summary of Completed Autonomous Execution:
- **Pre-registration frozen & tagged:** Git tag `eval-freeze-v1` committed on branch `audit-revision`.
- **M1–M9 Mutation Operators implemented:** 250 valid mutants generated, 20 excluded with manifestation logs in `eval/results/exclusion_log.csv`.
- **Benign Controls:** 30 semantics-preserving control mutants generated in `eval/results/benign_manifest.json`.
- **Formal Evaluation Benchmark:** Run across all 6 detector suites; results written to `paper_revision/results/formal_seeded_defect_benchmark.json`.
- **Deployed Forecaster on Authentic Delta Windows ($N=120$):** Run with cluster-robust Diebold–Mariano test; negative skill disclosed ($p=0.0013$, WAPE $100.00\%$ vs.\ $82.90\%$).
- **Grouped Permutation Importance & Threshold Sensitivity:** Evaluated on clean model and deployed model; written to `clean_model_permutation_results.json` and `threshold_grid.json`.
- **Phase 2 AST Algorithm:** Fully formalized in LaTeX inside `paper_revised.tex` Table III (Algorithm 2: AST-TIV).
- **Git Defect Archaeology:** Traced all 9 defects via `git log -S`; written to `paper_revision/results/defect_history.json`.
- **Paper Self-Consistency & References:** Scenario $R^2$ corrected to 0.998, Wilson CIs corrected to $[0.0\%, 56.1\%]$, rater strata corrected to $n=18/14$, RGB tensor probe described accurately, references [51] and [52] corrected to official published titles/authors.
- **Title, Abstract, and Conclusion:** Toned down title ("with Seeded-Defect and External Evaluation"), honest reporting of deployed vs research model, and formal mutant benchmark statistics.
- **LaTeX Compilation:** PDF recompiled cleanly (19 pages).
