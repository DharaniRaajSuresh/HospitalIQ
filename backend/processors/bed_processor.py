"""
WHAT THIS FILE DOES:
PREPARES raw bed CSV data for ML training. This is a data pipeline that:
1. Loads raw bed data from CSV files
2. Cleans missing values and outliers
3. Engineers features (month sin/cos, lag values, rolling averages)
4. Encodes categorical variables (state names → numbers)
5. Splits into train/test sets
6. Saves processed data for model training

This runs during the TRAINING phase (not when you use the website).
The trained model is saved as bed_model.pkl and loaded later for predictions.

BedDataProcessor - Concrete processor for bed data
"""

import logging
import math

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from backend.core.base_processor import BaseDataProcessor

logger = logging.getLogger(__name__)


class BedDataProcessor(BaseDataProcessor):
    """
    Concrete processor for hospital bed data.    """

    def __init__(self):
        super().__init__(
            raw_data_path="ml_pipeline/data/raw/beds_raw.csv",
            processed_data_path="ml_pipeline/data/processed/bed_data_processed.csv"
        )
        self._scaler = MinMaxScaler()
        self._state_encoding = {}

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean bed data: handle nulls, fix dtypes."""
        logger.info("🧹 Cleaning bed data...")

        if df.empty:
            return df

        # Fill nulls
        df["occupancy_rate"] = df["occupancy_rate"].fillna(0)
        df["available_beds"] = df["available_beds"].fillna(0)
        df["total_beds"] = df["total_beds"].fillna(100)

        # Ensure numeric types
        df["total_beds"] = pd.to_numeric(df["total_beds"], errors="coerce").fillna(100)
        df["available_beds"] = pd.to_numeric(df["available_beds"], errors="coerce").fillna(0)
        df["occupancy_rate"] = pd.to_numeric(df["occupancy_rate"], errors="coerce").fillna(0)

        # Clip occupancy to [0, 100]
        df["occupancy_rate"] = df["occupancy_rate"].clip(0, 100)

        # Remove duplicates
        df = df.drop_duplicates()

        # Ensure month/year are int
        if "recorded_month" in df.columns:
            df["recorded_month"] = pd.to_numeric(df["recorded_month"], errors="coerce").fillna(1).astype(int)
        if "recorded_year" in df.columns:
            df["recorded_year"] = pd.to_numeric(df["recorded_year"], errors="coerce").fillna(2020).astype(int)

        logger.info(f"✅ Cleaned {len(df)} records")
        return df

    def encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features."""
        logger.info("🔤 Encoding categorical features...")

        if df.empty:
            return df

        # Encode states
        if "state" in df.columns:
            unique_states = sorted(df["state"].unique())
            self._state_encoding = {state: i for i, state in enumerate(unique_states)}
            df["state_encoded"] = df["state"].map(self._state_encoding)

        # Encode ward types
        if "ward_type" in df.columns:
            ward_mapping = {"ICU": 0, "General": 1, "Maternity": 2, "Emergency": 3}
            df["ward_type_encoded"] = df["ward_type"].map(ward_mapping)

        logger.info(f"✅ Encoded {len(self._state_encoding)} unique states")
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create new features from existing data."""
        logger.info("⚙️  Engineering features...")

        if df.empty:
            return df

        # Cyclical month features
        if "recorded_month" in df.columns:
            df["month_sin"] = df["recorded_month"].apply(lambda m: math.sin(2 * math.pi * m / 12))
            df["month_cos"] = df["recorded_month"].apply(lambda m: math.cos(2 * math.pi * m / 12))

        # Year normalized
        if "recorded_year" in df.columns:
            min_year = df["recorded_year"].min()
            df["year_normalized"] = (df["recorded_year"] - min_year) / (df["recorded_year"].max() - min_year + 1)

        # Season flag (1=winter, 2=spring, 3=summer, 4=monsoon)
        if "recorded_month" in df.columns:
            df["season_flag"] = df["recorded_month"].apply(
                lambda m: 1 if m in [12, 1, 2] else (2 if m in [3, 4, 5] else (3 if m in [6, 7] else 4))
            )

        # Aggregate to state-ward-month level for clean lag features
        if "available_beds" in df.columns and "state" in df.columns and "ward_type" in df.columns:
            monthly = df.groupby(
                ["state", "ward_type", "recorded_year", "recorded_month"]
            )["available_beds"].mean().reset_index()
            monthly = monthly.sort_values(["state", "ward_type", "recorded_year", "recorded_month"])
            monthly["lag_1_month"] = monthly.groupby(["state", "ward_type"])["available_beds"].shift(1).fillna(0)
            monthly["lag_3_month"] = monthly.groupby(["state", "ward_type"])["available_beds"].shift(3).fillna(0)
            monthly["lag_6_month"] = monthly.groupby(["state", "ward_type"])["available_beds"].shift(6).fillna(0)
            monthly["rolling_mean_3"] = monthly.groupby(["state", "ward_type"])["available_beds"].transform(
                lambda x: x.rolling(3, min_periods=1).mean()
            )
            monthly["rolling_mean_6"] = monthly.groupby(["state", "ward_type"])["available_beds"].transform(
                lambda x: x.rolling(6, min_periods=1).mean()
            )
            # Merge lag features back to original rows
            df = df.merge(
                monthly[["state", "ward_type", "recorded_year", "recorded_month",
                         "lag_1_month", "lag_3_month", "lag_6_month",
                         "rolling_mean_3", "rolling_mean_6"]],
                on=["state", "ward_type", "recorded_year", "recorded_month"],
                how="left"
            )

        logger.info("✅ Engineered new features")
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numerical features."""
        logger.info("📏 Normalizing features...")

        if df.empty:
            return df

        # Only normalize total_beds (lag features and other features keep their scale)
        if "total_beds" in df.columns:
            df["total_beds_scaled"] = self._scaler.fit_transform(df[["total_beds"]])

        logger.info("✅ Normalized total_beds column")
        return df

    def get_feature_columns(self) -> list:
        """Return feature column names (NO target leakage)."""
        return [
            "month_sin", "month_cos", "year_normalized",
            "season_flag", "state_encoded", "ward_type_encoded",
            "lag_1_month", "lag_3_month", "lag_6_month",
            "rolling_mean_3", "rolling_mean_6"
        ]

    def get_target_column(self) -> str:
        """Return target column name."""
        return "available_beds"
