"""Shared ML utilities: cross-validation, hyperparameter tuning, MLflow tracking, model versioning"""
import os, json, logging
from datetime import datetime
import joblib
import numpy as np
from sklearn.model_selection import cross_val_score, KFold, TimeSeriesSplit

logger = logging.getLogger(__name__)
MODEL_DIR = "ml_pipeline/data/models"

try:
    import mlflow
    import mlflow.sklearn
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False


def setup_mlflow(experiment_name, tracking_uri=None):
    if not MLFLOW_AVAILABLE:
        logger.info("MLflow not installed, skipping experiment tracking")
        return None
    uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
    mlflow.set_tracking_uri(uri)
    try:
        mlflow.set_experiment(experiment_name)
    except:
        mlflow.create_experiment(experiment_name)
        mlflow.set_experiment(experiment_name)
    return mlflow


def cross_validate(model, X, y, cv=5, scoring="r2", time_series=False):
    if time_series:
        splitter = TimeSeriesSplit(n_splits=min(cv, len(X) // 2))
    else:
        splitter = KFold(n_splits=cv, shuffle=True, random_state=42)
    scores = cross_val_score(model, X, y, cv=splitter, scoring=scoring)
    logger.info(f"  CV ({'time-series' if time_series else 'standard'}): {scores.mean():.4f} ± {scores.std():.4f}")
    return scores


def save_model_versioned(model, name, metrics=None, params=None):
    os.makedirs(MODEL_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    version = f"{name}_{timestamp}"
    path = os.path.join(MODEL_DIR, f"{version}.pkl")
    joblib.dump(model, path)
    joblib.dump(model, os.path.join(MODEL_DIR, f"{name}.pkl"))
    metadata = {
        "version": version, "timestamp": timestamp,
        "model_name": name, "metrics": metrics or {},
        "params": params or {},
    }
    with open(os.path.join(MODEL_DIR, f"{name}_metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)
    logger.info(f"  Model saved: {name}.pkl (version: {version})")
    if MLFLOW_AVAILABLE and mlflow.active_run():
        mlflow.log_artifact(path)
    return version
