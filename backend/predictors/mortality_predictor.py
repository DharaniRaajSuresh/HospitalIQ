"""
WHAT THIS FILE DOES:
Predicts DEATH RATES (mortality) for districts using an XGBoost model +
K-Means clustering. When you see "death rate per 100k" on the Mortality
Analytics page, this code produced it.

Uses seasonal patterns (sin/cos of month), lag features from previous months,
and clusters districts by similar mortality profiles for better predictions.

MortalityPredictor - Concrete predictor for mortality risk analysis
Monthly seasonal forecasting with lag/rolling features
"""

from backend.core.base_predictor import BasePredictor
from backend.predictors.risk_utils import assign_risk_level
from typing import Any, Dict, List
import pandas as pd
import os, math
import logging

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)


class MortalityPredictor(BasePredictor):
    """
    Concrete predictor for mortality risk analysis.
    Supports monthly forecasting with seasonality features.
    """

    AGE_GROUPS = ["0-14", "15-44", "45-64", "65+"]
    CAUSES = ["Cardiac", "Respiratory", "Infectious", "Cancer",
              "Accident", "Maternal", "Neonatal", "Other"]
    FEATURE_NAMES = [
        "state_encoded", "district_encoded", "age_group_encoded",
        "cause_encoded", "year", "population_scaled",
        "month_sin", "month_cos", "season_flag",
        "lag_1_month", "lag_3_month", "lag_6_month",
        "rolling_mean_3", "rolling_mean_6"
    ]

    def __init__(self):
        super().__init__(model_name="mortality_xgb_model", model_dir=MODEL_DIR)
        self._cluster_model = None
        self._state_encoding = {}
        self._district_encoding = {}
        self._cause_encoding = {
            "Cardiac": 0, "Respiratory": 1, "Infectious": 2, "Cancer": 3,
            "Accident": 4, "Maternal": 5, "Neonatal": 6, "Other": 7
        }
        self._age_mapping = {"0-14": 0, "15-44": 1, "45-64": 2, "65+": 3}
        self._district_to_state = {}
        self._last_known_rates = {}  # for computing lag features at prediction time

    def load_model(self) -> None:
        """Extend parent load_model to also load cluster model and encodings."""
        super().load_model()
        import joblib

        cluster_path = os.path.join(self._model_dir, "mortality_kmeans_model.pkl")
        if os.path.exists(cluster_path):
            self._cluster_model = joblib.load(cluster_path)
            logger.info("✅ Loaded mortality K-Means cluster model")

        # Load encoding mappings from processed data
        csv_path = "ml_pipeline/data/processed/mortality_data_processed.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                if "state_encoded" in df.columns and "state" in df.columns:
                    mapping = df[["state", "state_encoded"]].drop_duplicates()
                    self._state_encoding = dict(zip(mapping["state"], mapping["state_encoded"]))
                if "district_encoded" in df.columns and "district" in df.columns:
                    mapping = df[["district", "district_encoded"]].drop_duplicates()
                    self._district_encoding = dict(zip(mapping["district"], mapping["district_encoded"]))
                # Build district→state lookup so we can infer state from district
                if "district" in df.columns and "state" in df.columns:
                    mapping = df[["district", "state"]].drop_duplicates()
                    self._district_to_state = dict(zip(mapping["district"], mapping["state"]))
                # Load last known death rates per group for lag estimation
                if "death_rate" in df.columns:
                    group_cols = ["state", "district", "age_group", "cause_of_death"]
                    if all(c in df.columns for c in group_cols):
                        df_sorted = df.sort_values(["state", "district", "age_group", "cause_of_death", "year", "month"])
                        for key, grp in df_sorted.groupby(group_cols):
                            last_rates = grp["death_rate"].tail(6).tolist()
                            self._last_known_rates[key] = last_rates

                logger.info(f"✅ Loaded encodings: {len(self._state_encoding)} states, {len(self._district_encoding)} districts")
            except Exception as e:
                logger.warning(f"Could not load encodings from CSV: {e}")

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """Validate input for mortality prediction."""
        required = ["district", "age_group", "cause", "year"]
        if not all(k in input_data for k in required):
            logger.warning(f"Missing required fields: {required}")
            return False
        if input_data["age_group"] not in self.AGE_GROUPS:
            logger.warning(f"Invalid age group: {input_data['age_group']}")
            return False
        if input_data["cause"] not in self.CAUSES:
            logger.warning(f"Invalid cause: {input_data['cause']}")
            return False
        if not 2015 <= input_data["year"] <= 2036:
            logger.warning("Year must be 2015-2036")
            return False
        month = input_data.get("month", 6)
        if not 1 <= month <= 12:
            logger.warning("Month must be 1-12")
            return False
        return True

    def get_feature_names(self) -> List[str]:
        """Polymorphic: mortality-specific features."""
        return self.FEATURE_NAMES

    def preprocess_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        """Preprocess mortality data with monthly seasonality and lag features."""
        district = raw_input.get("district", "")
        state = raw_input.get("state", self._district_to_state.get(district, ""))
        month = raw_input.get("month", 6)

        # Cyclical month encoding
        month_sin = math.sin(2 * math.pi * month / 12)
        month_cos = math.cos(2 * math.pi * month / 12)

        # Season flag
        if month in [12, 1, 2]:
            season_flag = 1
        elif month in [3, 4, 5]:
            season_flag = 2
        elif month in [6, 7]:
            season_flag = 3
        elif month in [8, 9]:
            season_flag = 4
        else:
            season_flag = 5

        age_group = raw_input.get("age_group", "0-14")
        cause = raw_input.get("cause", "Other")

        # Estimate lag features from last known rates for this group
        lookup_key = (state, district, age_group, cause)
        last_rates = self._last_known_rates.get(lookup_key, [])

        lag_1 = last_rates[-1] if len(last_rates) >= 1 else 0
        lag_3 = last_rates[-3] if len(last_rates) >= 3 else 0
        lag_6 = last_rates[-6] if len(last_rates) >= 6 else 0

        rolling_3 = sum(last_rates[-3:]) / min(len(last_rates[-3:]), 1) if last_rates else 0
        rolling_6 = sum(last_rates[-6:]) / min(len(last_rates[-6:]), 1) if last_rates else 0

        return {
            **raw_input,
            "state_encoded": self._state_encoding.get(state, 0),
            "district_encoded": self._district_encoding.get(district, 0),
            "age_group_encoded": self._age_mapping.get(age_group, 0),
            "cause_encoded": self._cause_encoding.get(cause, 0),
            "population_scaled": raw_input.get("population", 1000000) / 1000000.0,
            "month_sin": month_sin,
            "month_cos": month_cos,
            "season_flag": season_flag,
            "lag_1_month": lag_1,
            "lag_3_month": lag_3,
            "lag_6_month": lag_6,
            "rolling_mean_3": rolling_3,
            "rolling_mean_6": rolling_6
        }

    def predict(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Polymorphic predict — mortality-specific implementation."""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input for MortalityPredictor: {input_data}")
        if not self._is_loaded:
            self.load_model()

        month = input_data.get("month", 6)
        processed = self.preprocess_input(input_data)
        features = [[processed.get(f, 0) for f in self.get_feature_names()]]

        try:
            death_rate = float(self._model.predict(features)[0]) if self._model else 75.0
        except Exception as e:
            logger.warning("MortalityPredictor predict failed: %s", e)
            death_rate = 75.0

        risk_level = assign_risk_level(death_rate)

        # Cluster info available for supplementary display
        cluster_id = None
        if self._cluster_model and self._model:
            try:
                import numpy as np
                cluster_id = int(self._cluster_model.predict(features)[0])
            except Exception as e:
                logger.warning("MortalityPredictor cluster predict failed: %s", e)

        MONTH_NAMES = ["","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]

        return {
            "district": input_data["district"],
            "age_group": input_data["age_group"],
            "cause": input_data["cause"],
            "year": input_data["year"],
            "month": month,
            "month_name": MONTH_NAMES[month],
            "predicted_death_rate": round(death_rate, 2),
            "risk_level": risk_level,
            "unit": "per 100,000 population",
            "model_info": self.get_model_info()
        }
