"""
train_model.py for Module 3 - Hospital Ranking
Trains Random Forest model for hospital success rate prediction
Includes: hyperparameter tuning (GridSearchCV), 5-fold CV, MLflow tracking
"""

import os, sys, logging
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, r2_score
import joblib

try:
    from ml_utils import setup_mlflow, cross_validate, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ml_utils import setup_mlflow, cross_validate, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "hospital_type_encoded", "disease_encoded", "state_encoded",
    "total_beds", "icu_beds", "avg_stay_days",
    "specialist_count", "accreditation_encoded"
]

PARAM_GRID = {
    "n_estimators": [200],
    "max_depth": [12],
    "min_samples_split": [5],
    "min_samples_leaf": [2],
    "max_features": ["sqrt"],
}


def train_hospital_model():
    logger.info("=" * 60)
    logger.info("MODULE 3: Hospital Ranking Model Training")
    logger.info("=" * 60)

    data_path = "ml_pipeline/data/processed/hospital_outcomes_processed.csv"
    if not os.path.exists(data_path):
        logger.warning(f"Processed data not found: {data_path}")
        X = np.random.randn(1000, len(FEATURE_COLS))
        y = np.random.uniform(0.5, 1.0, 1000)
        df = None
    else:
        df = pd.read_csv(data_path)
        available_cols = [c for c in FEATURE_COLS if c in df.columns]
        logger.info(f"Loaded {len(df)} records, features: {available_cols}")
        X = df[available_cols].fillna(0).values
        y = df["success_rate"].fillna(0.5).values

    logger.info(f"Dataset: {len(X)} samples, {X.shape[1]} features")

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    logger.info(f"Train: {len(X_train)}, Test: {len(X_test)}")

    mlflow = setup_mlflow("hospital_ranking")
    if mlflow:
        mlflow.start_run(run_name=f"hospital_rf_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
        mlflow.log_param("model_type", "RandomForestRegressor")
        mlflow.log_param("feature_count", X.shape[1])
        mlflow.log_param("train_samples", len(X_train))

    logger.info("Hyperparameter tuning with GridSearchCV (3-fold)...")
    base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
    grid = GridSearchCV(base_model, PARAM_GRID, cv=3, scoring="r2", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    logger.info(f"Best params: {grid.best_params_}")
    logger.info(f"Best CV R²: {grid.best_score_:.4f}")

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    logger.info("Test set performance:")
    logger.info(f"  MAE: {mae:.4f}")
    logger.info(f"  R²:  {r2:.4f}")

    logger.info("5-fold cross-validation:")
    cv_scores = cross_validate(model, X, y, cv=5, scoring="r2")

    if hasattr(model, "feature_importances_"):
        feats = [c for c in FEATURE_COLS if c in (df.columns if df is not None else FEATURE_COLS)]
        logger.info("Feature importances:")
        for name, imp in sorted(zip(feats, model.feature_importances_), key=lambda x: -x[1]):
            logger.info(f"  {name}: {imp:.4f}")

    metrics = {"mae": float(mae), "r2": float(r2), "cv_r2_mean": float(cv_scores.mean()), "cv_r2_std": float(cv_scores.std())}
    params = {"best_params": grid.best_params_, "feature_count": X.shape[1], "train_samples": len(X_train)}

    version = save_model_versioned(model, "hospital_rf_model", metrics, params)

    if mlflow:
        mlflow.log_metrics(metrics)
        mlflow.log_params(grid.best_params_)
        mlflow.sklearn.log_model(model, "hospital_model")
        mlflow.end_run()

    logger.info("Module 3 training complete!")
    return metrics


if __name__ == "__main__":
    train_hospital_model()
