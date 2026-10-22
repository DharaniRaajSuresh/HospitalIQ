"""Shared ML utilities: cross-validation, hyperparameter tuning, MLflow tracking,
model versioning, bootstrap confidence intervals, and forecast comparison tests."""
import json
import logging
import os
from datetime import datetime

import joblib
import numpy as np
from scipy import stats
from sklearn.model_selection import KFold, TimeSeriesSplit, cross_val_score

logger = logging.getLogger(__name__)
MODEL_DIR = "ml_pipeline/data/models"


# ---------------------------------------------------------------------------
# Statistical utilities (bootstrap CI and Diebold-Mariano test)
# ---------------------------------------------------------------------------

def bootstrap_mape(y_true, y_pred, n_bootstraps=1000, alpha=0.05,
                   random_state=42):
    """Compute MAPE with bootstrap 95% confidence interval.

    Parameters
    ----------
    y_true : array-like
        Ground-truth target values.
    y_pred : array-like
        Predicted values.
    n_bootstraps : int
        Number of bootstrap resamples (default 1000).
    alpha : float
        Significance level; CI is [alpha/2, 1-alpha/2] (default 0.05 → 95% CI).
    random_state : int or None
        Seed for reproducibility.

    Returns
    -------
    lower : float
        Lower bound of CI (percentage).
    upper : float
        Upper bound of CI (percentage).
    point : float
        Point estimate MAPE (percentage).
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred = np.asarray(y_pred, dtype=np.float64)

    # Exclude entries where y_true == 0 to avoid division by zero
    mask = y_true != 0
    y_true, y_pred = y_true[mask], y_pred[mask]

    ape = np.abs((y_true - y_pred) / y_true) * 100.0
    point = float(np.mean(ape))

    rng = np.random.RandomState(random_state)
    n = len(ape)
    boot_mapes = np.empty(n_bootstraps)
    for i in range(n_bootstraps):
        idx = rng.randint(0, n, size=n)
        boot_mapes[i] = np.mean(ape[idx])

    lower = float(np.percentile(boot_mapes, 100.0 * alpha / 2))
    upper = float(np.percentile(boot_mapes, 100.0 * (1 - alpha / 2)))
    return lower, upper, point


def diebold_mariano(y_true, y_pred1, y_pred2, h=1):
    """Diebold-Mariano test for equal predictive accuracy.

    Tests H0: E[d_t] = 0 where d_t = e1_t^2 - e2_t^2 (squared-error loss).
    Uses the Harvey, Leybourne & Newbold (1997) small-sample correction and
    Newey-West HAC variance estimator with bandwidth h-1 for h-step-ahead
    forecasts.

    Parameters
    ----------
    y_true : array-like
        Ground-truth values.
    y_pred1 : array-like
        Predictions from model 1.
    y_pred2 : array-like
        Predictions from model 2.
    h : int
        Forecast horizon (step-ahead); controls HAC bandwidth (default 1).

    Returns
    -------
    dm_stat : float
        Diebold-Mariano test statistic.
    p_value : float
        Two-tailed p-value.
    """
    y_true = np.asarray(y_true, dtype=np.float64)
    y_pred1 = np.asarray(y_pred1, dtype=np.float64)
    y_pred2 = np.asarray(y_pred2, dtype=np.float64)

    e1 = y_true - y_pred1
    e2 = y_true - y_pred2
    d = e1 ** 2 - e2 ** 2  # loss differential (squared-error loss)

    n = len(d)
    d_bar = np.mean(d)

    # Newey-West HAC variance with bandwidth h-1
    gamma_0 = np.mean((d - d_bar) ** 2)
    gamma_sum = 0.0
    for k in range(1, h):
        gamma_k = np.mean((d[k:] - d_bar) * (d[:-k] - d_bar))
        gamma_sum += 2.0 * gamma_k
    var_d = (gamma_0 + gamma_sum) / n

    if var_d <= 0:
        return 0.0, 1.0

    dm_stat = d_bar / np.sqrt(var_d)

    # Harvey, Leybourne & Newbold (1997) small-sample correction
    hlnc = np.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    dm_stat_corrected = dm_stat * hlnc

    p_value = 2.0 * stats.t.sf(np.abs(dm_stat_corrected), df=n - 1)
    return float(dm_stat_corrected), float(p_value)

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
    except Exception:
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
