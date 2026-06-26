"""
train_model.py for Module 2 - Mortality Analysis
Trains XGBoost regressor + KMeans clustering for mortality risk
Includes: hyperparameter tuning (GridSearchCV), 5-fold CV, MLflow tracking
"""

import logging
import os
import sys

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV
from xgboost import XGBRegressor

try:
    from ml_utils import MLFLOW_AVAILABLE, MODEL_DIR, cross_validate, save_model_versioned, setup_mlflow
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ml_utils import cross_validate, save_model_versioned, setup_mlflow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "state_encoded", "district_encoded", "age_group_encoded",
    "cause_encoded", "year", "population_scaled",
    "month_sin", "month_cos", "season_flag",
    "lag_1_month", "lag_3_month", "lag_6_month",
    "rolling_mean_3", "rolling_mean_6"
]


def train_mortality_models():
    logger.info("=" * 60)
    logger.info("MODULE 2: Mortality Analysis Model Training (XGBoost)")
    logger.info("=" * 60)

    data_path = "ml_pipeline/data/processed/mortality_data_processed.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Training data not found at {data_path}. "
            "Run the data generation pipeline first:\n"
            "  python ml_pipeline/module2_mortality/generate_data.py\n"
            "  python ml_pipeline/real_data_ingest.py\n"
            "Or from project root:\n"
            "  python run_pipeline.py"
        )
    else:
        df = pd.read_csv(data_path)
        available_cols = [c for c in FEATURE_COLS if c in df.columns]
        logger.info(f"Loaded {len(df)} records, features: {available_cols}")
        X = df[available_cols].fillna(0).values
        y = df["death_rate"].fillna(0).values

    # Subsample for faster training (still representative at scale)
    if len(X) > 50000:
        idx = np.random.RandomState(42).choice(len(X), 50000, replace=False)
        X, y = X[idx], y[idx]
        logger.info(f"Subsampled to {len(X)} for fast training")

    # Chronological split to avoid temporal data leakage
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    logger.info(f"Train: {len(X_train)} (chronological), Test: {len(X_test)}")

    mlflow = setup_mlflow("mortality_analysis")
    if mlflow:
        mlflow.start_run(run_name=f"mortality_xgb_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
        mlflow.log_param("model_type", "XGBRegressor")
        mlflow.log_param("feature_count", X.shape[1])
        mlflow.log_param("train_samples", len(X_train))

    logger.info("Hyperparameter tuning with GridSearchCV (3-fold)...")
    PARAM_GRID = {
        "n_estimators": [100, 200],
        "max_depth": [4, 6],
        "learning_rate": [0.05, 0.1],
        "subsample": [0.8],
        "colsample_bytree": [0.8],
        "reg_lambda": [1.0, 5.0],
        "min_child_weight": [5],
    }
    base_model = XGBRegressor(random_state=42, n_jobs=-1, verbosity=0)
    grid = GridSearchCV(base_model, PARAM_GRID, cv=2, scoring="r2", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    logger.info(f"Best params: {grid.best_params_}")
    logger.info(f"Best CV R²: {grid.best_score_:.4f}")

    y_pred = model.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    logger.info("Test set performance:")
    logger.info(f"  RMSE: {rmse:.2f}")
    logger.info(f"  R²:   {r2:.4f}")

    logger.info("5-fold time-series cross-validation:")
    cv_scores = cross_validate(model, X, y, cv=5, scoring="r2", time_series=True)

    if hasattr(model, "feature_importances_"):
        feats = [c for c in FEATURE_COLS if c in (df.columns if df is not None else FEATURE_COLS)]
        logger.info("Feature importances:")
        for name, imp in sorted(zip(feats, model.feature_importances_), key=lambda x: -x[1]):
            logger.info(f"  {name}: {imp:.4f}")

    logger.info("Training K-Means for risk clustering...")
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)
    n_clusters = len(set(clusters))
    logger.info(f"K-Means clusters: {n_clusters}")

    metrics = {"rmse": float(rmse), "r2": float(r2), "cv_r2_mean": float(cv_scores.mean()), "cv_r2_std": float(cv_scores.std()), "kmeans_clusters": n_clusters}
    params = {"feature_count": X.shape[1], "train_samples": len(X_train)}

    save_model_versioned(model, "mortality_xgb_model", metrics, params)
    save_model_versioned(kmeans, "mortality_kmeans_model", {"clusters": n_clusters}, {"n_clusters": 4, "random_state": 42})

    if mlflow:
        mlflow.log_metrics({k: v for k, v in metrics.items() if isinstance(v, (int, float))})
        mlflow.sklearn.log_model(model, "mortality_model")
        mlflow.sklearn.log_model(kmeans, "mortality_kmeans")
        mlflow.end_run()

    logger.info("Module 2 training complete!")
    return metrics


if __name__ == "__main__":
    train_mortality_models()
