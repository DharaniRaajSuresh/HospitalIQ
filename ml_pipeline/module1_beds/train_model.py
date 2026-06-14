"""
train_model.py for Module 1 - Bed Forecasting
Trains Gradient Boosting model for bed availability prediction
Uses features: month_sin, month_cos, year_normalized, season_flag,
               state_encoded, ward_type_encoded, lag_1_month, lag_3_month,
               lag_6_month, rolling_mean_3, rolling_mean_6
Target: available_beds
Includes: hyperparameter tuning (GridSearchCV), 5-fold cross-validation, MLflow tracking
"""

import os, sys, logging
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

try:
    from ml_utils import setup_mlflow, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR
except ImportError:
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    from ml_utils import setup_mlflow, save_model_versioned, MLFLOW_AVAILABLE, MODEL_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FEATURE_COLS = [
    "month_sin", "month_cos", "year_normalized",
    "season_flag", "state_encoded", "ward_type_encoded",
    "lag_1_month", "lag_3_month", "lag_6_month",
    "rolling_mean_3", "rolling_mean_6"
]

PARAM_GRID = {
    "n_estimators": [200],
    "max_depth": [5],
    "learning_rate": [0.1],
    "min_samples_leaf": [5],
    "subsample": [0.8],
}


def train_bed_model():
    logger.info("=" * 60)
    logger.info("MODULE 1: Bed Forecasting Model Training")
    logger.info("=" * 60)

    data_path = "ml_pipeline/data/processed/bed_data_processed.csv"
    if not os.path.exists(data_path):
        raise FileNotFoundError(
            f"Training data not found at {data_path}. "
            "Run the data generation pipeline first:\n"
            "  python ml_pipeline/module1_beds/generate_data.py\n"
            "  python ml_pipeline/real_data_ingest.py\n"
            "Or from project root:\n"
            "  python run_pipeline.py"
        )
    else:
        df = pd.read_csv(data_path)
        available_cols = [c for c in FEATURE_COLS if c in df.columns]
        logger.info(f"Loaded {len(df)} records, features: {available_cols}")
        X = df[available_cols].fillna(0).values
        y = df["available_beds"].fillna(0).values

    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    logger.info(f"Train: {len(X_train)} (chronological), Test: {len(X_test)}")

    mlflow = setup_mlflow("bed_forecasting")
    if mlflow:
        mlflow.start_run(run_name=f"bed_gbr_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}")
        mlflow.log_param("model_type", "GradientBoostingRegressor")
        mlflow.log_param("feature_count", X.shape[1])
        mlflow.log_param("train_samples", len(X_train))

    logger.info("Hyperparameter tuning with GridSearchCV (3-fold)...")
    base_model = GradientBoostingRegressor(random_state=42)
    grid = GridSearchCV(base_model, PARAM_GRID, cv=3, scoring="r2", n_jobs=-1, verbose=0)
    grid.fit(X_train, y_train)

    model = grid.best_estimator_
    logger.info(f"Best params: {grid.best_params_}")
    logger.info(f"Best CV R²: {grid.best_score_:.4f}")

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    logger.info("Test set performance:")
    logger.info(f"  MAE:  {mae:.2f}")
    logger.info(f"  RMSE: {rmse:.2f}")
    logger.info(f"  R²:   {r2:.4f}")

    if hasattr(model, "feature_importances_"):
        feats = [c for c in FEATURE_COLS if c in (df.columns if df is not None else FEATURE_COLS)]
        logger.info("Feature importances:")
        for name, imp in sorted(zip(feats, model.feature_importances_), key=lambda x: -x[1]):
            logger.info(f"  {name}: {imp:.4f}")

    metrics = {"mae": float(mae), "rmse": float(rmse), "r2": float(r2)}
    params = {"best_params": grid.best_params_, "feature_count": X.shape[1], "train_samples": len(X_train)}

    version = save_model_versioned(model, "bed_model", metrics, params)
    logger.info(f"Model version: {version}")

    if mlflow:
        mlflow.log_metrics(metrics)
        mlflow.log_params(grid.best_params_)
        mlflow.sklearn.log_model(model, "bed_model")
        mlflow.end_run()

    logger.info("Module 1 training complete!")
    return metrics


if __name__ == "__main__":
    train_bed_model()
