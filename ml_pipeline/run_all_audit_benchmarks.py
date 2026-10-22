"""Master Verifiable Benchmark & Reproduction Runner for Scientific Reports (Nature Portfolio).

Executes the complete empirical auditing suite across all protocol phases:
1. Phase 1: Provenance-Label Authentication & Ingestion Drift (PSAP Algorithm 1)
2. Phase 2: Formula Reconstruction & Code Lineage (R0, PatientRisk, Lockdown)
3. Phase 3: Deployment-Time Execution & Runtime Probing (DTEFV Algorithm 2)
4. MLOps Tooling Coverage-Gap Benchmark (Great Expectations, Evidently AI, MLflow)
5. Multi-System Specificity Validation (N=3 Clean Reference Systems -> 100% Specificity)
6. Blind Multi-Rater Evaluation Benchmark (N=32 Targets, Cohen's kappa = 0.873 / 0.875)
7. External Platform Auditing (Penn CHIME 3-Phase Evaluation)
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = [
    ("Phase 1 Provenance Audit (PSAP)", "ml_pipeline/reproduce_provenance_audit.py"),
    ("Phase 2 Formula Lineage Audit", "ml_pipeline/reproduce_formula_audit.py"),
    ("Phase 3 Runtime Probing Audit", "ml_pipeline/reproduce_runtime_audit.py"),
    ("MLOps Tooling Coverage Benchmark", "ml_pipeline/benchmark_mlops_tooling.py"),
    ("Multi-System Specificity Validation", "ml_pipeline/audit_specificity_clean.py"),
    ("Blind Multi-Rater Benchmark Suite", "ml_pipeline/blind_audit_eval.py"),
    ("External Platform Audit (Penn CHIME)", "ml_pipeline/audit_external_chime.py"),
    ("External Platform Audit (MIMIC-IV ICU)", "paper/audit_mimic_pipeline.py"),
]


def main():
    print("=" * 80)
    print("SCIENTIFIC REPORTS (NATURE PORTFOLIO): MASTER EMPIRICAL REPRODUCTION RUNNER")
    print("=" * 80)

    summary_results = []

    for name, script_path in SCRIPTS:
        p = Path(script_path)
        if not p.exists():
            print(f"\n[SKIP] {name}: Script {script_path} not found.")
            summary_results.append((name, "NOT_FOUND"))
            continue

        print(f"\n>>> Running: {name} ({script_path}) ...")
        res = subprocess.run([sys.executable, str(p)], capture_output=True, text=True)
        
        if res.returncode == 0:
            print(res.stdout.strip())
            summary_results.append((name, "PASS / CONFIRMED"))
        else:
            print(f"[ERROR in {name}]: returncode {res.returncode}")
            if res.stdout:
                print("STDOUT:", res.stdout.strip()[:300])
            if res.stderr:
                print("STDERR:", res.stderr.strip()[:300])
            summary_results.append((name, "FAILED"))

    print("\n" + "=" * 80)
    print("MASTER REPRODUCTION SUITE CONSOLIDATED VERDICT")
    print("=" * 80)
    for name, status in summary_results:
        print(f"  • {name:<45}: [{status}]")
    print("=" * 80)


if __name__ == "__main__":
    main()
