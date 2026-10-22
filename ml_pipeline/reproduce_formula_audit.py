"""Measure deterministic-target reconstruction for the audited artifacts.

The script uses controlled synthetic probes for R0, Patient Risk, and
Lockdown. It does not claim that these probes represent clinical data. Scenario
training/inference alignment is reported from source inspection because the
primary outbreak database is currently corrupt.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from ml_pipeline.train_patient_risk import compute_risk_labels

DISEASE_BASELINE_R0 = {
    "COVID-19": 2.5, "Ebola": 1.8, "H1N1": 1.5,
    "SARS": 3.0, "Nipah": 1.8, "Marburg": 1.7,
}
R0_METADATA = Path("ml_pipeline/data/models/r0_metadata.pkl")
R0_MODEL = Path("ml_pipeline/data/models/r0_model.pkl")
PATIENT_MODEL = Path("ml_pipeline/data/models/patient_risk_model.pkl")
PATIENT_METADATA = Path("ml_pipeline/data/models/patient_risk_metadata.pkl")
LOCKDOWN_MODEL = Path("ml_pipeline/data/models/lockdown_model.pkl")
LOCKDOWN_SCALER = Path("ml_pipeline/data/models/lockdown_scaler.pkl")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def r0_formula(disease: str, years_since_2020: int, vaccination_rate: float, mutation_factor: float, population_millions: float) -> float:
    density_mod = 1.0 + 0.08 * (population_millions / 100.0)
    value = DISEASE_BASELINE_R0[disease] * (0.96 ** years_since_2020)
    value *= 1.0 - 0.40 * vaccination_rate
    value *= 1.0 + 0.30 * (mutation_factor - 1.0)
    value *= density_mod
    return max(0.3, min(6.0, round(value, 4)))


def audit_r0() -> dict[str, Any]:
    metadata = joblib.load(R0_METADATA)
    model = joblib.load(R0_MODEL)
    rows: list[dict[str, Any]] = []
    for disease, baseline in DISEASE_BASELINE_R0.items():
        disease_encoding = metadata.get("disease_encoding", {})
        disease_code = disease_encoding.get(disease, 0)
        state = next(iter(metadata.get("state_encoding", {"Maharashtra": 0})))
        state_code = metadata.get("state_encoding", {}).get(state, 0)
        density = metadata.get("state_population_density", {}).get(state, 100_000)
        population_millions = density / 1_000_000 * 10
        for years in (0, 4, 10, 20):
            vaccination = 1.0 / (1.0 + math.exp(-0.45 * (years - 4)))
            for mutation in (0.5, 1.0, 1.8, 2.5):
                features = np.array([[density, vaccination, mutation, years, (2020 + years - 2017) / 20.0, disease_code, state_code]])
                predicted = float(model.predict(features)[0])
                expected = r0_formula(disease, years, vaccination, mutation, population_millions)
                rows.append({"disease": disease, "years_since_2020": years, "mutation_factor": mutation, "expected_formula": expected, "model_prediction": predicted, "absolute_error": abs(predicted - expected)})
    frame = pd.DataFrame(rows)
    return {"n": len(frame), "mae": float(frame.absolute_error.mean()), "max_absolute_error": float(frame.absolute_error.max()), "rows": frame.to_dict(orient="records"), "model_sha256": sha256_file(R0_MODEL), "metadata_sha256": sha256_file(R0_METADATA)}


def audit_patient_risk() -> dict[str, Any]:
    model_bundle = joblib.load(PATIENT_MODEL)
    metadata = joblib.load(PATIENT_METADATA)
    rng = np.random.default_rng(42)
    rows: list[dict[str, Any]] = []
    for _ in range(100):
        row = {
            "age": int(rng.integers(1, 101)), "blood_group": int(rng.integers(0, 8)), "gender_male": int(rng.integers(0, 2)),
            "num_preexisting": int(rng.integers(0, 5)), "num_doses": int(rng.integers(0, 4)), "has_covid_vaccine": 1,
            "last_vaccine_days": int(rng.integers(0, 1000)), "recent_travel": int(rng.integers(0, 2)), "num_trips": int(rng.integers(0, 4)),
            "fam_high_risk": int(rng.integers(0, 2)), "fam_total": int(rng.integers(0, 4)), "virus_fatality": float(rng.uniform(0.01, 0.55)),
            "virus_reproductive": float(rng.uniform(1.0, 3.5)), "vaccine_available": 1, "vaccine_effectiveness": float(rng.uniform(0.5, 0.9)),
        }
        expected = compute_risk_labels(row)
        vector = np.array([[row[name] for name in metadata["feature_names"]]], dtype=np.float32)
        actual = []
        for target in metadata["target_names"]:
            bundle = model_bundle[target]
            predictions = [bundle[key].predict(vector)[0] for key in ("xgb", "rf", "gb") if key in bundle]
            actual.append(float(np.mean(predictions)))
        rows.append({"expected_risk_score": expected[0], "model_risk_score": actual[0], "risk_error": abs(expected[0] - actual[0]), "expected_hospitalization": expected[1], "model_hospitalization": actual[1], "hospitalization_error": abs(expected[1] - actual[1]), "expected_mortality": expected[2], "model_mortality": actual[2], "mortality_error": abs(expected[2] - actual[2])})
    frame = pd.DataFrame(rows)
    return {"n": len(frame), "risk_score_mae": float(frame.risk_error.mean()), "hospitalization_mae": float(frame.hospitalization_error.mean()), "mortality_mae": float(frame.mortality_error.mean()), "model_sha256": sha256_file(PATIENT_MODEL), "metadata_sha256": sha256_file(PATIENT_METADATA), "rows": frame.to_dict(orient="records")}


def audit_lockdown() -> dict[str, Any]:
    rng = np.random.default_rng(42)
    features = pd.DataFrame(rng.uniform(0, 100, size=(300, 6)), columns=["avg_r0", "avg_cfr", "total_cases", "total_deaths", "total_bed_demand", "total_icu_demand"])
    severity = sum(features[column].rank(pct=True) * weight for column, weight in [("total_deaths", 0.35), ("avg_cfr", 0.25), ("total_cases", 0.10), ("avg_r0", 0.05), ("total_bed_demand", 0.10), ("total_icu_demand", 0.15)])
    labels = (severity >= severity.quantile(0.70)).astype(int).to_numpy()
    model = joblib.load(LOCKDOWN_MODEL)
    scaler = joblib.load(LOCKDOWN_SCALER)
    predictions = model.predict(scaler.transform(features.to_numpy()))
    return {"n": len(features), "label_rate": float(labels.mean()), "agreement": float(np.mean(predictions == labels)), "model_sha256": sha256_file(LOCKDOWN_MODEL), "scaler_sha256": sha256_file(LOCKDOWN_SCALER)}


def scenario_source_status() -> dict[str, Any]:
    source = Path("ml_pipeline/train_scenario.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    return {"source_sha256": sha256_file(source), "contains_avg_cfr": "avg_cfr" in names, "contains_avg_r0": "avg_r0" in names, "database_reproduction_status": "blocked_by_database_integrity_failure"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("paper/results/formula_audit.json"))
    args = parser.parse_args()
    result = {"status": "completed", "r0": audit_r0(), "patient_risk": audit_patient_risk(), "lockdown": audit_lockdown(), "scenario": scenario_source_status()}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"status": result["status"], "r0_n": result["r0"]["n"], "patient_n": result["patient_risk"]["n"], "lockdown_agreement": result["lockdown"]["agreement"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
