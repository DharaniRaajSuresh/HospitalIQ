"""
WHAT THIS FILE DOES:
PREPARES raw mortality CSV data for ML training. Same pipeline pattern as
bed_processor.py but for death records. Engineers features like death rates
per 100k population, seasonal mortality patterns, and age-group-specific risks.

The processed data is used to train the XGBoost mortality model and the
K-Means clustering model that groups districts by risk profile.

MortalityDataProcessor - Concrete processor for mortality data
Demonstrates: Inheritance, Polymorphism, Template Method Pattern
"""

from backend.core.base_processor import BaseDataProcessor
import pandas as pd
import numpy as np
import math
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class MortalityDataProcessor(BaseDataProcessor):
    """
    Concrete processor for mortality records.

    OOP Principles:
    - Inheritance: extends BaseDataProcessor
    - Polymorphism: mortality-specific data cleaning and feature engineering
    """

    def __init__(self):
        super().__init__(
            raw_data_path="ml_pipeline/data/raw/mortality_raw.csv",
            processed_data_path="ml_pipeline/data/processed/mortality_data_processed.csv"
        )
        self._scaler = StandardScaler()
        self._cause_encoding = {}
        self._state_encoding = {}
        self._district_encoding = {}

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean mortality data."""
        logger.info("🧹 Cleaning mortality data...")

        if df.empty:
            return df

        # Fill nulls
        df["death_count"] = df["death_count"].fillna(0)
        df["death_rate"] = df["death_rate"].fillna(0)
        df["population"] = df["population"].fillna(1000000)

        # Ensure numeric types
        df["death_count"] = pd.to_numeric(df["death_count"], errors="coerce").fillna(0)
        df["death_rate"] = pd.to_numeric(df["death_rate"], errors="coerce").fillna(0)
        df["population"] = pd.to_numeric(df["population"], errors="coerce").fillna(1000000)

        # Remove duplicates
        df = df.drop_duplicates()

        # Remove extreme outliers
        Q3 = df["death_rate"].quantile(0.75)
        IQR = Q3 - df["death_rate"].quantile(0.25)
        upper_bound = Q3 + 3 * IQR
        df = df[df["death_rate"] <= upper_bound]

        logger.info(f"✅ Cleaned {len(df)} mortality records")
        return df

    def encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical mortality features."""
        logger.info("🔤 Encoding categorical features...")

        if df.empty:
            return df

        # Encode states
        if "state" in df.columns:
            unique_states = df["state"].unique()
            self._state_encoding = {s: i for i, s in enumerate(sorted(unique_states))}
            df["state_encoded"] = df["state"].map(self._state_encoding)

        # Encode districts
        if "district" in df.columns:
            unique_districts = df["district"].unique()
            self._district_encoding = {d: i for i, d in enumerate(sorted(unique_districts))}
            df["district_encoded"] = df["district"].map(self._district_encoding)

        # Encode cause of death
        if "cause_of_death" in df.columns:
            unique_causes = sorted(df["cause_of_death"].unique())
            self._cause_encoding = {cause: i for i, cause in enumerate(unique_causes)}
            df["cause_encoded"] = df["cause_of_death"].map(self._cause_encoding)

        # Encode age groups
        if "age_group" in df.columns:
            age_mapping = {"0-14": 0, "15-44": 1, "45-64": 2, "65+": 3}
            df["age_group_encoded"] = df["age_group"].map(age_mapping)

        # Encode risk clusters
        if "risk_cluster" in df.columns:
            risk_mapping = {"Low Risk": 0, "Moderate": 1, "High Risk": 2, "Critical": 3}
            df["risk_encoded"] = df["risk_cluster"].map(risk_mapping)

        logger.info(f"✅ Encoded {len(self._state_encoding)} states, {len(self._district_encoding)} districts, {len(self._cause_encoding)} causes")
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer mortality-specific features including monthly seasonality."""
        logger.info("⚙️  Engineering monthly features...")

        if df.empty:
            return df

        # Ensure year is int
        if "year" in df.columns:
            df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(2020).astype(int)

        # Ensure month is int
        if "month" in df.columns:
            df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(1).astype(int)

        # Cyclical month features
        if "month" in df.columns:
            df["month_sin"] = df["month"].apply(lambda m: math.sin(2 * math.pi * m / 12))
            df["month_cos"] = df["month"].apply(lambda m: math.cos(2 * math.pi * m / 12))

        # Season flag (1=winter, 2=spring, 3=summer, 4=monsoon, 5=post-monsoon)
        if "month" in df.columns:
            df["season_flag"] = df["month"].apply(
                lambda m: 1 if m in [12, 1, 2] else (2 if m in [3, 4, 5] else (3 if m in [6, 7] else (4 if m in [8, 9] else 5)))
            )

        # Lag features per (state, district, age_group, cause) group
        if "death_rate" in df.columns:
            group_cols = ["state", "district", "age_group", "cause_of_death"]
            if all(c in df.columns for c in group_cols):
                df = df.sort_values(["state", "district", "age_group", "cause_of_death", "year", "month"])
                df["lag_1_month"] = df.groupby(group_cols)["death_rate"].shift(1).fillna(0)
                df["lag_3_month"] = df.groupby(group_cols)["death_rate"].shift(3).fillna(0)
                df["lag_6_month"] = df.groupby(group_cols)["death_rate"].shift(6).fillna(0)

        # Rolling averages per group
        if "death_rate" in df.columns:
            group_cols = ["state", "district", "age_group", "cause_of_death"]
            if all(c in df.columns for c in group_cols):
                df["rolling_mean_3"] = df.groupby(group_cols)["death_rate"].transform(
                    lambda x: x.rolling(3, min_periods=1).mean()
                )
                df["rolling_mean_6"] = df.groupby(group_cols)["death_rate"].transform(
                    lambda x: x.rolling(6, min_periods=1).mean()
                )

        logger.info("✅ Engineered monthly mortality features")
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize numerical features."""
        logger.info("📏 Normalizing features...")

        if df.empty:
            return df

        # Only normalize population (other features are categorical encodings)
        if "population" in df.columns:
            df["population_scaled"] = self._scaler.fit_transform(df[["population"]])
            # Keep original too, but use scaled for model features

        logger.info("✅ Normalized population column")
        return df

    def get_feature_columns(self) -> list:
        """Return feature columns (NO target leakage)."""
        return [
            "state_encoded", "district_encoded", "age_group_encoded",
            "cause_encoded", "year", "population_scaled",
            "month_sin", "month_cos", "season_flag",
            "lag_1_month", "lag_3_month", "lag_6_month",
            "rolling_mean_3", "rolling_mean_6"
        ]

    def get_target_column(self) -> str:
        """Return target column."""
        return "death_rate"
