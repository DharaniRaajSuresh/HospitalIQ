"""
WHAT THIS FILE DOES:
Ranks hospitals by SUCCESS RATE using a Random Forest model. Used by the
Hospital Rankings page to show which hospitals perform best for specific
diseases (Cardiac, Diabetes, Cancer, etc.).

Unlike BedPredictor which forecasts future values, this model evaluates
and scores existing hospitals based on features like: bed count, doctor
count, accreditation, stay duration, and historical success rates.

HospitalPredictor - Concrete predictor for hospital success rate ranking
Demonstrates: Inheritance, Polymorphism
"""

import logging
import os
from typing import Any

import pandas as pd

from backend.core.base_predictor import BasePredictor

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)


class HospitalPredictor(BasePredictor):
    """
    Concrete predictor for hospital success rate ranking.

    OOP Principles:
    - Inheritance: extends BasePredictor
    - Polymorphism: predict(), validate_input() specific to hospitals
    """

    DISEASES = ["Cardiac", "Diabetes", "Dengue", "Tuberculosis",
                "Pneumonia", "Cancer", "Stroke", "Hepatitis", "Malaria", "Typhoid"]
    HOSPITAL_TYPES = ["Govt", "Private", "Trust", "NGO"]
    FEATURE_NAMES = [
        "hospital_type_encoded", "disease_encoded", "state_encoded",
        "total_beds", "icu_beds", "avg_stay_days",
        "specialist_count", "accreditation_encoded"
    ]

    def __init__(self):
        super().__init__(model_name="hospital_rf_model", model_dir=MODEL_DIR)
        self._outcomes_df = None
        self._disease_encoding = {d: i for i, d in enumerate(sorted(self.DISEASES))}
        self._type_encoding = {"Govt": 0, "Private": 1, "Trust": 2, "NGO": 3}
        self._accred_encoding = {"NABH": 3, "JCI": 3, "ISO": 2, "None": 1}
        self._state_encoding = {}

    def load_model(self) -> None:
        """Extend parent to load hospital outcomes data and encodings."""
        super().load_model()

        csv_path = "ml_pipeline/data/processed/hospital_outcomes_processed.csv"
        if os.path.exists(csv_path):
            try:
                self._outcomes_df = pd.read_csv(csv_path)
                logger.info(f"✅ Loaded {len(self._outcomes_df)} hospital outcomes records")

                # Load state encoding
                if "state" in self._outcomes_df.columns and "state_encoded" in self._outcomes_df.columns:
                    mapping = self._outcomes_df[["state", "state_encoded"]].drop_duplicates()
                    self._state_encoding = dict(zip(mapping["state"], mapping["state_encoded"]))
                    logger.info(f"✅ Loaded {len(self._state_encoding)} state encodings")

                # Load disease encoding
                if "disease" in self._outcomes_df.columns and "disease_encoded" in self._outcomes_df.columns:
                    mapping = self._outcomes_df[["disease", "disease_encoded"]].drop_duplicates()
                    self._disease_encoding.update(dict(zip(mapping["disease"], mapping["disease_encoded"])))

            except Exception as e:
                logger.warning(f"Could not load hospital outcomes: {e}")
                self._outcomes_df = pd.DataFrame()
        else:
            self._outcomes_df = pd.DataFrame()

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input for hospital ranking."""
        if "disease" not in input_data:
            logger.warning("Missing 'disease' field")
            return False
        if input_data["disease"] not in self._disease_encoding:
            logger.warning(f"Invalid disease: {input_data['disease']}")
            return False
        return True

    def get_feature_names(self) -> list[str]:
        """Polymorphic: hospital-specific features."""
        return self.FEATURE_NAMES

    def preprocess_input(self, raw_input: dict[str, Any]) -> dict[str, Any]:
        """Preprocess hospital ranking data."""
        return {
            **raw_input,
            "hospital_type_encoded": self._type_encoding.get(raw_input.get("hospital_type", "Private"), 0),
            "disease_encoded": self._disease_encoding.get(raw_input.get("disease", "Cardiac"), 0),
            "state_encoded": self._state_encoding.get(raw_input.get("state", ""), 0),
            "total_beds": raw_input.get("total_beds", 200),
            "icu_beds": raw_input.get("icu_beds", 20),
            "avg_stay_days": raw_input.get("avg_stay_days", 7),
            "specialist_count": raw_input.get("specialist_count", 10),
            "accreditation_encoded": self._accred_encoding.get(raw_input.get("accreditation", "None"), 1),
        }

    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Polymorphic predict — hospital ranking implementation."""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input for HospitalPredictor: {input_data}")
        if not self._is_loaded:
            self.load_model()

        # Use model prediction for success rate
        processed = self.preprocess_input(input_data)
        features = [[processed.get(f, 0) for f in self.get_feature_names()]]

        try:
            predicted_success = float(self._model.predict(features)[0]) if self._model else 0.75
            predicted_success = max(0.1, min(1.0, predicted_success))
        except Exception as e:
            logger.warning("HospitalPredictor predict failed: %s", e)
            predicted_success = 0.75

        # Also return rankings from actual data
        df = self._outcomes_df.copy()
        rankings = []
        if not df.empty and "disease" in df.columns:
            df = df[df["disease"] == input_data["disease"]]
            if input_data.get("state") and "state" in df.columns:
                df = df[df["state"] == input_data["state"]]
            if "hospital_score" in df.columns:
                df = df.sort_values("hospital_score", ascending=False)
            df["rank"] = range(1, len(df) + 1)
            top_n = input_data.get("top_n", 10)
            output_cols = [c for c in [
                "rank", "hospital_name", "district", "state",
                "hospital_type", "success_rate", "avg_stay_days",
                "hospital_score", "rating", "accreditation"
            ] if c in df.columns]
            if output_cols:
                rankings = df.head(top_n)[output_cols].to_dict(orient="records")

        return {
            "disease": input_data["disease"],
            "total_found": len(df) if not df.empty else 0,
            "predicted_success_rate": round(predicted_success, 4),
            "rankings": rankings,
            "model_info": self.get_model_info()
        }
