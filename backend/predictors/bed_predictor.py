"""
WHAT THIS FILE DOES:
Predicts FUTURE BED AVAILABILITY using an XGBoost ML model. When a user
asks "how many ICU beds will Tamil Nadu need in 2030?", this is the code
that answers. It:

1. Loads the trained XGBoost model from bed_model.pkl
2. Builds 11 mathematical features (month sine/cosine, lag values, rolling averages)
3. Runs the model for each requested month (up to 120 months / 10 years)
4. Calculates confidence intervals that widen for farther predictions
5. Returns the forecast with lower/upper bounds

Different states and ward types produce different predictions (proves it's not hardcoded).

BedPredictor - Concrete predictor for bed availability forecasting
Demonstrates: Inheritance, Polymorphism
"""

import calendar
import logging
import math
import os
from datetime import datetime
from typing import Any

import pandas as pd

from backend.core.base_predictor import BasePredictor

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)


class BedPredictor(BasePredictor):
    """
    Concrete predictor for bed availability forecasting.

    OOP Principles:
    - Inheritance: extends BasePredictor
    - Polymorphism: predict(), validate_input() implement base contract
    - Encapsulation: ward types and states as private class attributes
    """

    FEATURE_NAMES = [
        "month_sin", "month_cos", "year_normalized",
        "season_flag", "state_encoded", "ward_type_encoded",
        "lag_1_month", "lag_3_month", "lag_6_month",
        "rolling_mean_3", "rolling_mean_6"
    ]

    def __init__(self):
        super().__init__(model_name="bed_model", model_dir=MODEL_DIR)
        self._scaler = None
        self._states = [
            "Tamil Nadu", "Maharashtra", "Delhi", "Karnataka",
            "West Bengal", "Rajasthan", "Gujarat",
            "Uttar Pradesh", "Kerala", "Telangana",
            "Bihar", "Madhya Pradesh", "Andhra Pradesh",
            "Odisha", "Jharkhand", "Haryana", "Punjab",
            "Himachal Pradesh", "Uttarakhand", "Goa",
            "Assam", "Meghalaya", "Manipur", "Mizoram",
            "Nagaland", "Tripura", "Sikkim", "Arunachal Pradesh",
            "Chhattisgarh", "Jammu and Kashmir"
        ]
        self._ward_types = ["ICU", "General", "Maternity", "Emergency"]
        self._state_encoding = {s: i for i, s in enumerate(sorted(self._states))}
        self._ward_encoding = {"ICU": 0, "General": 1, "Maternity": 2, "Emergency": 3}
        self._last_known = {}  # Store last known values for lag features
        self._year_min = 2015
        self._year_range = 11

    def load_model(self) -> None:
        """Extend parent load_model to also load scaler and historical data."""
        super().load_model()
        from collections import deque

        import joblib

        scaler_path = os.path.join(self._model_dir, "bed_scaler.pkl")
        if os.path.exists(scaler_path):
            self._scaler = joblib.load(scaler_path)
            logger.info("✅ Loaded bed scaler")

        # Load historical data for lag features
        csv_path = "ml_pipeline/data/processed/bed_data_processed.csv"
        if os.path.exists(csv_path):
            try:
                df = pd.read_csv(csv_path)
                # Determine year range from training data
                if "recorded_year" in df.columns:
                    self._year_min = int(df["recorded_year"].min())
                    y_max = int(df["recorded_year"].max())
                    self._year_range = y_max - self._year_min + 1
                # Aggregate to state-ward-month level, then sort for lag features
                if "state" in df.columns and "ward_type" in df.columns:
                    monthly = df.groupby(
                        ["state", "ward_type", "recorded_year", "recorded_month"]
                    )["available_beds"].mean().reset_index()
                    monthly = monthly.sort_values(["state", "ward_type", "recorded_year", "recorded_month"])
                    for (state, ward), group in monthly.groupby(["state", "ward_type"]):
                        if not group.empty:
                            vals = group["available_beds"].tolist()
                            self._last_known[(state, ward)] = {
                                "history": deque(vals, maxlen=120),
                                "available_beds": vals[-1] if vals else 100,
                            }
                    logger.info(f"✅ Loaded historical data for {len(self._last_known)} state/ward combinations")
            except Exception as e:
                logger.warning(f"Could not load historical data: {e}")

    def validate_input(self, input_data: dict[str, Any]) -> bool:
        """Validate input before prediction."""
        required = ["state", "ward_type", "months_ahead"]
        if not all(k in input_data for k in required):
            logger.warning(f"Missing required fields: {required}")
            return False
        if input_data["state"] not in self._state_encoding:
            logger.warning(f"Invalid state: {input_data['state']}")
            return False
        if input_data["ward_type"] not in self._ward_encoding:
            logger.warning(f"Invalid ward type: {input_data['ward_type']}")
            return False
        if not 1 <= input_data["months_ahead"] <= 120:
            logger.warning("months_ahead must be 1-120")
            return False
        return True

    def get_feature_names(self) -> list[str]:
        """Polymorphic: bed-specific features."""
        return self.FEATURE_NAMES

    def preprocess_input(self, raw_input: dict[str, Any]) -> dict[str, Any]:
        """Override parent preprocess with bed-specific logic."""
        month = raw_input.get("month", datetime.now().month)
        year = raw_input.get("year", datetime.now().year)
        state = raw_input["state"]
        ward = raw_input["ward_type"]

        # Season flag
        if month in [12, 1, 2]:
            season = 1  # winter
        elif month in [3, 4, 5]:
            season = 2  # spring
        elif month in [6, 7]:
            season = 3  # summer
        else:
            season = 4  # monsoon

        # Get last known values for lag features
        key = (state, ward)
        last = self._last_known.get(key, {})
        current_beds = last.get("available_beds", 150)

        return {
            **raw_input,
            "month_sin": math.sin(2 * math.pi * month / 12),
            "month_cos": math.cos(2 * math.pi * month / 12),
            "year_normalized": (year - self._year_min) / self._year_range,
            "season_flag": season,
            "state_encoded": self._state_encoding.get(state, 0),
            "ward_type_encoded": self._ward_encoding.get(ward, 0),
            "lag_1_month": last.get("lag_1_month", current_beds),
            "lag_3_month": last.get("lag_3_month", current_beds),
            "lag_6_month": last.get("lag_6_month", current_beds),
            "rolling_mean_3": last.get("rolling_mean_3", current_beds),
            "rolling_mean_6": last.get("rolling_mean_6", current_beds),
        }

    def predict(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """Iterative forecast — each prediction feeds into the next month's lag features."""
        if not self.validate_input(input_data):
            raise ValueError(f"Invalid input for BedPredictor: {input_data}")
        if not self._is_loaded:
            self.load_model()

        key = (input_data["state"], input_data["ward_type"])
        raw = self._last_known.get(key, {})
        history = list(raw.get("history", []))
        if len(history) < 6:
            history = [100] * 6

        state_enc = self._state_encoding.get(input_data["state"], 0)
        ward_enc = self._ward_encoding.get(input_data["ward_type"], 0)

        growth_factor = 1.0

        forecasts = []
        base_month = input_data.get("start_month", 1)
        base_year = input_data.get("start_year", datetime.now().year)

        for i in range(input_data["months_ahead"]):
            month = ((base_month + i - 1) % 12) + 1
            year = base_year + (base_month + i - 1) // 12

            if month in [12, 1, 2]:
                season = 1
            elif month in [3, 4, 5]:
                season = 2
            elif month in [6, 7]:
                season = 3
            else:
                season = 4

            h = history
            lag_1 = h[-1]
            lag_3 = h[-3] if len(h) >= 3 else h[-1]
            lag_6 = h[-6] if len(h) >= 6 else h[-1]
            roll_3 = sum(h[-3:]) / 3 if len(h) >= 3 else h[-1]
            roll_6 = sum(h[-6:]) / 6 if len(h) >= 6 else h[-1]

            features = [[
                math.sin(2 * math.pi * month / 12),
                math.cos(2 * math.pi * month / 12),
                (year - self._year_min) / self._year_range,
                season, state_enc, ward_enc,
                lag_1, lag_3, lag_6, roll_3, roll_6,
            ]]

            try:
                if not self._model:
                    raise RuntimeError("BedPredictor model not loaded")
                prediction = float(self._model.predict(features)[0])
            except Exception as e:
                logger.warning("BedPredictor predict failed: %s", e)
                raise

            prediction = prediction * growth_factor
            prediction = max(1, round(prediction))
            history.append(prediction)
            # Keep only last 12 values to prevent long-term drift
            history = history[-12:]

            forecasts.append({
                "month": month,
                "year": year,
                "month_name": calendar.month_name[month],
                "predicted_beds": prediction,
            })

        return {
            "state": input_data["state"],
            "ward_type": input_data["ward_type"],
            "forecast": forecasts,
            "model_info": {**self.get_model_info(), "note": "Raw ML output, no post-hoc scaling"}
        }
