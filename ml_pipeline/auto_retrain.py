"""
Auto-Retrain Pipeline — FAANG-grade automated ML model retraining with
performance comparison, staging promotion/rollback, and full history tracking.
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

import joblib
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auto_retrain")

MODEL_DIR = "ml_pipeline/data/models"
RETRAIN_DIR = "ml_pipeline/data/retraining"
MIN_IMPROVEMENT_THRESHOLD = 0.01

RETRAINABLE_MODELS = [
    {
        "name": "bed_model",
        "display": "Bed Forecasting",
        "script": "ml_pipeline/module1_beds/train_model.py",
        "eval_type": "regression",
        "primary_metric": "r2",
        "higher_is_better": True,
    },
    {
        "name": "mortality_xgb_model",
        "display": "Mortality Analysis",
        "script": "ml_pipeline/module2_mortality/train_model.py",
        "eval_type": "regression",
        "primary_metric": "r2",
        "higher_is_better": True,
    },
    {
        "name": "hospital_rf_model",
        "display": "Hospital Ranking",
        "script": "ml_pipeline/module3_hospitals/train_model.py",
        "eval_type": "regression",
        "primary_metric": "r2",
        "higher_is_better": True,
    },
    {
        "name": "risk_model",
        "display": "Risk Scoring",
        "script": "ml_pipeline/train_risk.py",
        "eval_type": "regression",
        "primary_metric": "test_r2",
        "higher_is_better": True,
    },
    {
        "name": "forecast_cases_model",
        "display": "Forecast (Cases)",
        "script": "ml_pipeline/train_forecast.py",
        "eval_type": "forecast",
        "primary_metric": "test_mape",
        "higher_is_better": False,
    },
]

os.makedirs(RETRAIN_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# History / Status persistence
# ---------------------------------------------------------------------------

def _load_json(path: str, default: Any = None) -> Any:
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return default if default is not None else []


def _save_json(path: str, data: Any):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def get_history() -> list[dict]:
    return _load_json(os.path.join(RETRAIN_DIR, "retraining_history.json"), [])


def append_history(entry: dict):
    hist = get_history()
    hist.append(entry)
    _save_json(os.path.join(RETRAIN_DIR, "retraining_history.json"), hist)


def get_status() -> dict:
    return _load_json(os.path.join(RETRAIN_DIR, "retraining_status.json"), {
        "status": "idle", "last_run": None, "current_model": None,
    })


def set_status(**kwargs):
    status = get_status()
    status.update(kwargs)
    _save_json(os.path.join(RETRAIN_DIR, "retraining_status.json"), status)


# ---------------------------------------------------------------------------
# Training execution
# ---------------------------------------------------------------------------

def run_training_script(script_path: str) -> bool:
    logger.info(f"Running training script: {script_path}")
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True, text=True, encoding="utf-8",
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        env=env,
    )
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            logger.info(f"  [train] {line}")
    if result.returncode != 0:
        logger.error(f"Training script failed (exit={result.returncode}): {result.stderr[:500]}")
        return False
    return True


# ---------------------------------------------------------------------------
# Evaluation helpers
# ---------------------------------------------------------------------------

def _eval_regression(model, X, y) -> dict[str, float]:
    preds = model.predict(X)
    return {
        "mae": float(mean_absolute_error(y, preds)),
        "rmse": float(np.sqrt(mean_squared_error(y, preds))),
        "r2": float(r2_score(y, preds)),
    }


def _get_primary(model_cfg: dict, metrics: dict) -> float:
    key = model_cfg["primary_metric"]
    return metrics.get(key, 0.0)


def _is_better(model_cfg: dict, new_val: float, old_val: float) -> bool:
    if model_cfg["higher_is_better"]:
        return new_val > old_val + MIN_IMPROVEMENT_THRESHOLD
    return new_val < old_val - MIN_IMPROVEMENT_THRESHOLD


def _load_previous_metrics(model_name: str) -> dict | None:
    meta_path = os.path.join(MODEL_DIR, f"{model_name}_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            return json.load(f).get("metrics")
    return None


def _get_model_path(model_name: str) -> str:
    return os.path.join(MODEL_DIR, f"{model_name}.pkl")


def _backup_path(model_name: str) -> str:
    return os.path.join(MODEL_DIR, f"{model_name}_retrain_backup.pkl")


# ---------------------------------------------------------------------------
# Retrain a single model
# ---------------------------------------------------------------------------

def retrain_model(model_cfg: dict) -> dict:
    name = model_cfg["name"]
    display = model_cfg["display"]
    logger.info(f"{'='*60}")
    logger.info(f"RETRAINING: {display} ({name})")
    logger.info(f"{'='*60}")

    result = {
        "model_name": name,
        "display": display,
        "timestamp": datetime.now(UTC).isoformat(),
        "status": "failed",
        "previous_metrics": None,
        "new_metrics": None,
        "improvement": None,
        "promoted": False,
        "error": None,
    }

    source_path = _get_model_path(name)
    backup = _backup_path(name)

    if os.path.exists(source_path):
        shutil.copy2(source_path, backup)
        logger.info(f"Backed up current model to {backup}")

    success = run_training_script(model_cfg["script"])
    if not success:
        result["error"] = "Training script failed"
        if os.path.exists(backup):
            shutil.copy2(backup, source_path)
            logger.info(f"Restored backup after training failure")
        return result

    if not os.path.exists(source_path):
        result["error"] = "Training produced no model file"
        if os.path.exists(backup):
            shutil.copy2(backup, source_path)
        return result

    new_metrics = None
    meta_path = os.path.join(MODEL_DIR, f"{name}_metadata.json")
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
            new_metrics = meta.get("metrics")

    prev_metrics = _load_previous_metrics(name) if os.path.exists(backup) else None
    if prev_metrics is None:
        prev_metrics = new_metrics

    result["new_metrics"] = new_metrics
    result["previous_metrics"] = prev_metrics

    if new_metrics and prev_metrics:
        new_primary = _get_primary(model_cfg, new_metrics)
        old_primary = _get_primary(model_cfg, prev_metrics)
        result["improvement"] = round(new_primary - old_primary, 6)

        if _is_better(model_cfg, new_primary, old_primary):
            try:
                from backend.core.model_registry import get_registry
                registry = get_registry()
                registry.log_model(name, None, metrics=new_metrics)
                registry.generate_model_card(name, metrics=new_metrics,
                                            description=f"Auto-retrained {display}")
                logger.info(f"Promoted {name} — primary metric improved: {old_primary} -> {new_primary}")
                result["promoted"] = True
                os.makedirs(os.path.join(MODEL_DIR, "promoted"), exist_ok=True)
                marker = os.path.join(MODEL_DIR, "promoted", f"{name}_promoted.txt")
                with open(marker, "w") as f:
                    f.write(f"Promoted at {result['timestamp']}\nImprovement: {result['improvement']}")
            except Exception as e:
                logger.warning(f"Registry promotion skipped: {e}")
        else:
            logger.info(f"No significant improvement for {name}: {old_primary} -> {new_primary}")
            if os.path.exists(backup):
                shutil.copy2(backup, source_path)
                logger.info(f"Restored previous version (no improvement)")
                result["status"] = "skipped"
                return result

    result["status"] = "promoted" if result.get("promoted") else "completed"

    if os.path.exists(backup):
        os.remove(backup)

    return result


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------

def run_all(retrain_args: list[str] | None = None) -> list[dict]:
    set_status(status="running", started_at=datetime.now(UTC).isoformat())

    models_to_run = RETRAINABLE_MODELS
    if retrain_args:
        models_to_run = [m for m in RETRAINABLE_MODELS if m["name"] in retrain_args or m["display"].lower() in [a.lower() for a in retrain_args]]

    results = []
    for cfg in models_to_run:
        try:
            r = retrain_model(cfg)
            results.append(r)
            append_history(r)
        except Exception as e:
            logger.exception(f"Fatal error retraining {cfg['name']}: {e}")
            err_result = {
                "model_name": cfg["name"],
                "display": cfg["display"],
                "timestamp": datetime.now(UTC).isoformat(),
                "status": "failed",
                "error": str(e),
            }
            results.append(err_result)
            append_history(err_result)

    set_status(status="idle", last_run=datetime.now(UTC).isoformat(),
               last_results=results)
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-retrain ML models")
    parser.add_argument("--models", nargs="*", help="Specific models to retrain (default: all)")
    args = parser.parse_args()
    results = run_all(args.models)
    promoted = [r for r in results if r.get("promoted")]
    failed = [r for r in results if r["status"] == "failed"]
    print(f"\nResults: {len(results)} trained, {len(promoted)} promoted, {len(failed)} failed")
    for r in results:
        flag = "✅ PROMOTED" if r.get("promoted") else ("❌ FAILED" if r["status"] == "failed" else "➖ SKIPPED" if r["status"] == "skipped" else "✓ completed")
        impr = f" (Δ={r.get('improvement', 'N/A'):+.4f})" if r.get("improvement") is not None else ""
        print(f"  {flag} {r['display']}{impr}")
