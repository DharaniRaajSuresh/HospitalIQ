"""Execute deployment-shaped probes against the committed predictor artifacts.

This audit records tested calls, exceptions, artifact hashes, feature counts,
and output summaries. It does not infer universal behavior from one probe and
never mutates model artifacts or application data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

import joblib
import numpy as np

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend.predictors.bed_predictor import BedPredictor
from backend.predictors.forecast_predictor import ForecastPredictor
from backend.predictors.hospital_predictor import HospitalPredictor
from backend.predictors.lockdown_predictor import LockdownPredictor
from backend.predictors.mortality_predictor import MortalityPredictor
from backend.predictors.patient_risk_predictor import PatientRiskPredictor
from backend.predictors.r0_predictor import R0Predictor
from backend.predictors.risk_predictor import RiskPredictor
from backend.predictors.scenario_predictor import ScenarioPredictor


MODEL_DIR = Path("ml_pipeline/data/models")


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def payloads() -> dict[str, list[dict[str, Any]]]:
    return {
        "bed_model": [
            {"state": "Maharashtra", "ward_type": "ICU", "months_ahead": 1, "start_year": 2026, "start_month": 1},
            {"state": "Tamil Nadu", "ward_type": "General", "months_ahead": 2, "start_year": 2026, "start_month": 6},
            {"state": "Delhi", "ward_type": "Emergency", "months_ahead": 1, "start_year": 2027, "start_month": 12},
        ],
        "forecast_cases": [
            {"disease": "COVID-19", "state": "Maharashtra", "history": [(100, 2), (120, 3), (140, 4)], "months_ahead": 1, "start_year_month": [2026, 1]},
            {"disease": "Ebola", "state": "Bihar", "history": [(10, 1), (12, 1), (15, 2)], "months_ahead": 1, "start_year_month": [2026, 1]},
            {"disease": "SARS", "state": "Delhi", "history": [(30, 2), (28, 2), (35, 3)], "months_ahead": 1, "start_year_month": [2026, 1]},
        ],
        "hospital_rf_model": [
            {"disease": "Cardiac", "hospital_type": "Govt", "state": "Maharashtra", "total_beds": 500, "icu_beds": 50, "avg_stay_days": 6, "specialist_count": 25, "accreditation": "NABH", "top_n": 1},
            {"disease": "Diabetes", "hospital_type": "Private", "state": "Delhi", "total_beds": 300, "icu_beds": 30, "avg_stay_days": 5, "specialist_count": 15, "accreditation": "ISO", "top_n": 1},
            {"disease": "Cancer", "hospital_type": "Trust", "state": "Kerala", "total_beds": 700, "icu_beds": 70, "avg_stay_days": 8, "specialist_count": 40, "accreditation": "JCI", "top_n": 1},
        ],
        "mortality_xgb_model": [
            {"district": "Mumbai", "age_group": "45-64", "cause": "Respiratory", "year": 2030, "month": 6, "population": 1_000_000},
            {"district": "Mumbai", "age_group": "45-64", "cause": "Respiratory", "year": 2030, "month": 6, "population": 5_000_000},
            {"district": "Mumbai", "age_group": "45-64", "cause": "Respiratory", "year": 2030, "month": 6, "population": 50_000_000},
        ],
        "r0_model": [
            {"disease": "COVID-19", "state": "Maharashtra", "target_year": 2026, "mutation_factor": 1.0},
            {"disease": "Ebola", "state": "Bihar", "target_year": 2030, "mutation_factor": 1.2},
            {"disease": "SARS", "state": "Delhi", "target_year": 2028, "mutation_factor": 0.9},
        ],
        "lockdown_model": [
            {"avg_r0": 2.0, "avg_cfr": 1.5, "total_cases": 1000, "total_deaths": 20, "total_bed_demand": 200, "total_icu_demand": 40},
            {"avg_r0": 3.0, "avg_cfr": 4.0, "total_cases": 5000, "total_deaths": 200, "total_bed_demand": 800, "total_icu_demand": 150},
            {"avg_r0": 1.2, "avg_cfr": 0.5, "total_cases": 100, "total_deaths": 1, "total_bed_demand": 10, "total_icu_demand": 2},
        ],
        "scenario_cases": [
            {"disease": "COVID-19", "state": "Maharashtra", "target_year": 2027},
            {"disease": "Ebola", "state": "Bihar", "target_year": 2028},
            {"disease": "SARS", "state": "Delhi", "target_year": 2029},
        ],
        "patient_risk_model": [
            {"age": 35, "blood_group": 6, "gender_male": 1, "num_preexisting": 0, "num_doses": 2, "has_covid_vaccine": 1, "last_vaccine_days": 120, "recent_travel": 0, "num_trips": 0, "fam_high_risk": 0, "fam_total": 0, "virus_fatality": 0.02, "virus_reproductive": 1.2, "vaccine_available": 1, "vaccine_effectiveness": 0.8},
            {"age": 65, "blood_group": 0, "gender_male": 1, "num_preexisting": 3, "num_doses": 1, "has_covid_vaccine": 1, "last_vaccine_days": 500, "recent_travel": 1, "num_trips": 2, "fam_high_risk": 1, "fam_total": 2, "virus_fatality": 0.05, "virus_reproductive": 2.0, "vaccine_available": 1, "vaccine_effectiveness": 0.6},
            {"age": 12, "blood_group": 2, "gender_male": 0, "num_preexisting": 0, "num_doses": 0, "has_covid_vaccine": 0, "last_vaccine_days": 0, "recent_travel": 0, "num_trips": 0, "fam_high_risk": 0, "fam_total": 0, "virus_fatality": 0.01, "virus_reproductive": 1.1, "vaccine_available": 1, "vaccine_effectiveness": 0.8},
        ],
        "risk_model": [
            {"disease": "COVID-19", "state": "Maharashtra", "total_confirmed": 1000, "total_deaths": 20, "avg_cfr": 2.0, "avg_r0": 1.5, "total_bed_demand": 200, "total_icu_demand": 40, "peak_monthly_cases": 300, "total_beds": 1000, "bed_occupancy": 0.4, "hospital_count": 20},
            {"disease": "COVID-19", "state": "Maharashtra", "total_confirmed": 10000, "total_deaths": 500, "avg_cfr": 5.0, "avg_r0": 3.0, "total_bed_demand": 2000, "total_icu_demand": 400, "peak_monthly_cases": 3000, "total_beds": 1000, "bed_occupancy": 0.9, "hospital_count": 20},
            {"disease": "Ebola", "state": "Bihar", "total_confirmed": 100, "total_deaths": 10, "avg_cfr": 10.0, "avg_r0": 1.2, "total_bed_demand": 50, "total_icu_demand": 10, "peak_monthly_cases": 40, "total_beds": 500, "bed_occupancy": 0.2, "hospital_count": 10},
        ],
    }


def artifact_path(model_name: str) -> Path | None:
    direct = MODEL_DIR / f"{model_name}.pkl"
    if direct.exists():
        return direct
    if model_name == "forecast_cases":
        return MODEL_DIR / "forecast_cases_model.pkl"
    if model_name == "scenario_cases":
        return MODEL_DIR / "scenario_cases_model.pkl"
    return None


def model_contract(model_name: str) -> dict[str, Any]:
    path = artifact_path(model_name)
    contract: dict[str, Any] = {"artifact": str(path) if path else None, "artifact_sha256": sha256_file(path) if path else None}
    if path and path.exists():
        try:
            model = joblib.load(path)
            contract["n_features_in"] = getattr(model, "n_features_in_", None)
            contract["model_type"] = type(model).__name__
        except Exception as error:
            contract["load_error"] = f"{type(error).__name__}: {error}"
    return contract


def summarize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): summarize(item) for key, item in value.items() if key not in {"rankings", "forecast"}}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "first": summarize(value[0]) if value else None}
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    return value


def run_predictor(model_name: str, predictor: Any, input_data: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {"model": model_name, "input": input_data, "status": "failed"}
    try:
        if hasattr(predictor, "load_model") and not getattr(predictor, "is_loaded", False):
            predictor.load_model()
        output = predictor.predict(input_data)
        record.update({"status": "success", "output": summarize(output)})
    except Exception as error:
        record.update({
            "exception_type": type(error).__name__,
            "exception": str(error),
            "traceback": traceback.format_exc(),
        })
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("paper/results/runtime_audit"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    registry: dict[str, Callable[[], Any]] = {
        "bed_model": BedPredictor,
        "forecast_cases": ForecastPredictor,
        "hospital_rf_model": HospitalPredictor,
        "mortality_xgb_model": MortalityPredictor,
        "r0_model": R0Predictor,
        "lockdown_model": LockdownPredictor,
        "scenario_cases": ScenarioPredictor,
        "patient_risk_model": PatientRiskPredictor,
        "risk_model": RiskPredictor,
    }
    probe_map = payloads()
    records: list[dict[str, Any]] = []
    contracts: dict[str, Any] = {}
    for model_name, factory in registry.items():
        contracts[model_name] = model_contract(model_name)
        try:
            predictor = factory()
        except Exception as error:
            records.append({"model": model_name, "status": "factory_failed", "exception_type": type(error).__name__, "exception": str(error), "traceback": traceback.format_exc()})
            continue
        for index, input_data in enumerate(probe_map[model_name], start=1):
            record = run_predictor(model_name, predictor, input_data)
            record["probe_id"] = f"{model_name}:{index}"
            record["artifact_contract"] = contracts[model_name]
            records.append(record)

    summary = {
        "status": "completed",
        "models": sorted(registry),
        "total_calls": len(records),
        "successful_calls": sum(record["status"] == "success" for record in records),
        "failed_calls": sum(record["status"] != "success" for record in records),
        "contracts": contracts,
        "records": records,
    }
    (args.output_dir / "runtime_audit.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("status", "total_calls", "successful_calls", "failed_calls")}, indent=2))
    return 0 if summary["failed_calls"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
