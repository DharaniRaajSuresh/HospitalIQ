"""Standardized evaluation configuration for all ML models."""
from sklearn.model_selection import TimeSeriesSplit

CV_SPLITS = 5
CV = TimeSeriesSplit(n_splits=CV_SPLITS)
SCORING_REGRESSION = "neg_mean_squared_error"
SCORING_R2 = "r2"

# Regularized grid to reduce overfitting:
# - Reduced max_depth from [4,6] to [3,4]
# - Reduced learning_rate from [0.05,0.1] to [0.01,0.05]
# - Added reg_alpha (L1) and increased reg_lambda (L2)
# - Added min_child_weight for more conservative splits
DEFAULT_PARAM_GRID_XGB = {
    "max_depth": [3, 4],
    "learning_rate": [0.01, 0.05],
    "subsample": [0.7, 0.8],
    "colsample_bytree": [0.7, 0.8],
    "reg_alpha": [0.1, 1.0],
    "reg_lambda": [5.0, 10.0],
    "min_child_weight": [3, 7],
}
