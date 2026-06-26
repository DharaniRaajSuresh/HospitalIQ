"""
backend/predictors/forecast_predictor.py — XGBoost time-series forecast for
monthly pandemic trajectory. Uses lag features, seasonality, and disease params
to predict confirmed_cases and deaths for N months ahead.
"""

import logging
import math
import os

import joblib
import numpy as np

from backend.core.base_predictor import BasePredictor

logger = logging.getLogger("forecast")

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)

FEATURE_NAMES = [
    "month_sin", "month_cos", "year_normalized",
    "lag_1_cases", "lag_2_cases", "lag_3_cases",
    "lag_1_deaths", "lag_2_deaths",
    "cases_ma3", "cases_growth",
    "disease_cfr", "disease_r0",
    "state_beds", "state_hospitals",
    "disease_enc", "state_enc",
]

class ForecastPredictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="forecast_cases", model_dir=MODEL_DIR)
        self._deaths_model = None
        self._metadata = None

    def load_model(self):
        self._model = joblib.load(os.path.join(self._model_dir, "forecast_cases_model.pkl"))
        self._deaths_model = joblib.load(os.path.join(self._model_dir, "forecast_deaths_model.pkl"))
        self._metadata = joblib.load(os.path.join(self._model_dir, "forecast_metadata.pkl"))
        self._is_loaded = True

    def validate_input(self, input_data):
        required = ["disease", "state", "history", "months_ahead"]
        for key in required:
            if key not in input_data:
                return False
        if not isinstance(input_data["history"], list) or len(input_data["history"]) < 3:
            return False
        return True

    def get_feature_names(self):
        return FEATURE_NAMES

    def build_feature(self, history, disease_enc, state_enc, disease_cfr, disease_r0,
                      state_beds, state_hospitals, year, month):
        lag_c = [history[-1][0], history[-2][0], history[-3][0]]
        lag_d = [history[-1][1], history[-2][1]]

        m_sin = math.sin(2 * math.pi * month / 12)
        m_cos = math.cos(2 * math.pi * month / 12)
        year_norm = (year - 2017) / 15
        ma3 = sum(lag_c) / 3
        growth = (lag_c[0] - lag_c[1]) / max(lag_c[1], 1)

        return np.array([[
            m_sin, m_cos, year_norm,
            lag_c[0], lag_c[1], lag_c[2],
            lag_d[0], lag_d[1],
            ma3, growth,
            disease_cfr, disease_r0,
            state_beds, state_hospitals,
            disease_enc, state_enc,
        ]])

    def predict(self, input_data):
        if not self._is_loaded:
            try:
                self.load_model()
            except Exception as e:
                logger.warning("ForecastPredictor load_model failed: %s", e)
        if not self.validate_input(input_data):
            return {"forecast": [], "model": "forecast", "is_ml": False}
        if not self._is_loaded:
            return {"forecast": [], "model": "forecast", "is_ml": False}

        disease = input_data["disease"]
        state = input_data["state"]
        history = input_data["history"]
        months_ahead = max(1, input_data.get("months_ahead", 12))

        meta = self._metadata or {}
        d_enc = meta.get("disease_encoding", {}).get(disease, 0)
        s_enc = meta.get("state_encoding", {}).get(state, 0)
        dp = meta.get("disease_params", {}).get(disease, {})
        disease_cfr = dp.get("cfr", 2.5)
        disease_r0 = dp.get("r0", 1.1)
        cap = meta.get("state_beds", {}).get(state, {"total_beds": 1000, "hospitals": 10})
        if isinstance(cap, dict):
            state_beds = cap.get("total_beds", 1000)
            state_hospitals = cap.get("hospitals", 10)
        else:
            state_beds, state_hospitals = 1000, 10

        # History: list of (cases, deaths) tuples, most recent last
        try:
            hist_cases = [max(1, h[0]) for h in history[-3:]]
            hist_deaths = [max(0, h[1]) for h in history[-3:]]
        except (IndexError, TypeError):
            return {"forecast": [], "model": "forecast", "is_ml": False}

        # Determine start year/month from history's last entry
        if len(input_data.get("start_year_month", [])) == 2:
            cy, cm = input_data["start_year_month"]
        else:
            cy, cm = 2025, 1

        forecast = []
        curr_cases = list(hist_cases)
        curr_deaths = list(hist_deaths)

        for step in range(months_ahead):
            cm += 1
            if cm > 12:
                cm = 1
                cy += 1

            try:
                feat = self.build_feature(
                    list(zip(curr_cases, curr_deaths)),
                    d_enc, s_enc, disease_cfr, disease_r0,
                    state_beds, state_hospitals, cy, cm,
                )

                pred_cases = float(np.expm1(self._model.predict(feat)[0]))
                pred_deaths = float(np.expm1(self._deaths_model.predict(feat)[0]))

                pred_cases = max(1, int(round(pred_cases)))
                pred_deaths = max(0, int(round(pred_deaths)))

                forecast.append({
                    "year": cy, "month": cm,
                    "month_name": ["Jan","Feb","Mar","Apr","May","Jun",
                                   "Jul","Aug","Sep","Oct","Nov","Dec"][cm-1],
                    "confirmed_cases": pred_cases,
                    "deaths": pred_deaths,
                    "recovered": pred_cases - pred_deaths,
                    "bed_demand": int(pred_cases * 0.15),
                    "icu_demand": int(pred_cases * 0.075),
                    "projected": True,
                })

                curr_cases.append(pred_cases)
                curr_deaths.append(pred_deaths)
                curr_cases = curr_cases[-3:]
                curr_deaths = curr_deaths[-3:]

            except Exception as e:
                logger.warning(f"Forecast step {step}: {e}")
                break

        return {
            "forecast": forecast,
            "model": "XGBoost (time-series)",
            "is_ml": True,
            "features_used": FEATURE_NAMES,
        }
