"""
WHAT THIS FILE DOES:
PREPARES raw hospital outcome CSV data for ML training. Processes hospital
performance data — success rates, bed counts, accreditation status, patient
admissions — into features for the Random Forest ranking model.

HospitalDataProcessor - Concrete processor for hospital data
"""

import logging

import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from backend.core.base_processor import BaseDataProcessor

logger = logging.getLogger(__name__)


class HospitalDataProcessor(BaseDataProcessor):
    """
    Concrete processor for hospital outcomes and patient admission data.    """

    def __init__(self):
        super().__init__(
            raw_data_path="ml_pipeline/data/raw/hospital_outcomes_raw.csv",
            processed_data_path="ml_pipeline/data/processed/hospital_outcomes_processed.csv"
        )
        self._scaler = MinMaxScaler()
        self._disease_encoding = {}
        self._state_encoding = {}
        self._type_encoding = {"Govt": 0, "Private": 1, "Trust": 2, "NGO": 3}
        self._accred_encoding = {"NABH": 3, "JCI": 3, "ISO": 2, "None": 1}

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean hospital data."""
        logger.info("🧹 Cleaning hospital data...")

        if df.empty:
            return df

        # Fill nulls
        df["success_rate"] = df["success_rate"].fillna(0.5)
        df["avg_stay_days"] = df["avg_stay_days"].fillna(5)
        df["total_beds"] = df["total_beds"].fillna(100)
        df["icu_beds"] = df["icu_beds"].fillna(10)
        df["specialist_count"] = df["specialist_count"].fillna(5)

        # Ensure numeric types
        for col in ["success_rate", "avg_stay_days", "total_beds", "icu_beds", "specialist_count"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # Clip success rate to [0, 1]
        if "success_rate" in df.columns:
            df["success_rate"] = df["success_rate"].clip(0, 1)

        # Remove duplicates
        df = df.drop_duplicates()

        logger.info(f"✅ Cleaned {len(df)} hospital records")
        return df

    def encode_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode hospital categorical features."""
        logger.info("🔤 Encoding categorical features...")

        if df.empty:
            return df

        # Encode states
        if "state" in df.columns:
            unique_states = sorted(df["state"].unique())
            self._state_encoding = {state: i for i, state in enumerate(unique_states)}
            df["state_encoded"] = df["state"].map(self._state_encoding)

        # Encode diseases
        if "disease" in df.columns:
            unique_diseases = sorted(df["disease"].unique())
            self._disease_encoding = {disease: i for i, disease in enumerate(unique_diseases)}
            df["disease_encoded"] = df["disease"].map(self._disease_encoding)

        # Encode hospital types
        if "hospital_type" in df.columns:
            df["hospital_type_encoded"] = df["hospital_type"].map(self._type_encoding)

        # Encode accreditation
        if "accreditation" in df.columns:
            df["accreditation_encoded"] = df["accreditation"].map(self._accred_encoding)

        logger.info(f"✅ Encoded {len(self._state_encoding)} states, {len(self._disease_encoding)} diseases")
        return df

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer hospital-specific features."""
        logger.info("⚙️  Engineering features...")

        if df.empty:
            return df

        # Calculate hospital score (composite metric, used for ranking not as feature)
        if "success_rate" in df.columns and "avg_stay_days" in df.columns:
            stay_score = 1 / (df["avg_stay_days"].clip(lower=1))
            df["hospital_score"] = (df["success_rate"] * 0.5) + (stay_score * 0.3)

        logger.info("✅ Engineered hospital features")
        return df

    def normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize hospital features."""
        logger.info("📏 Normalizing features...")

        if df.empty:
            return df

        # Normalize numeric features
        numeric_cols = ["total_beds", "icu_beds", "avg_stay_days"]
        available_cols = [col for col in numeric_cols if col in df.columns]

        if available_cols:
            df[available_cols] = self._scaler.fit_transform(df[available_cols])

        logger.info(f"✅ Normalized {len(available_cols)} numeric columns")
        return df

    def get_feature_columns(self) -> list:
        """Return feature columns (NO target leakage)."""
        return [
            "hospital_type_encoded", "disease_encoded", "state_encoded",
            "total_beds", "icu_beds", "avg_stay_days",
            "specialist_count", "accreditation_encoded"
        ]

    def get_target_column(self) -> str:
        """Return target column."""
        return "success_rate"
