"""
scenario_predictor.py — XGBoost annual scenario model.
Predicts total annual cases/deaths given (state, disease, target_year).
Used to scale the monthly forecast trajectory per target year.
"""
import logging
import os

import joblib
import numpy as np

from backend.core.base_predictor import BasePredictor

logger = logging.getLogger("scenario")

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)

FEATURE_NAMES = ["target_year_norm", "avg_cfr", "avg_r0", "state_beds", "state_hospitals", "disease_enc", "state_enc"]

class ScenarioPredictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="scenario_cases", model_dir=MODEL_DIR)
        self._deaths_model = None
        self._metadata = None

    def load_model(self):
        self._model = joblib.load(os.path.join(self._model_dir, "scenario_cases_model.pkl"))
        self._deaths_model = joblib.load(os.path.join(self._model_dir, "scenario_deaths_model.pkl"))
        self._metadata = joblib.load(os.path.join(self._model_dir, "scenario_metadata.pkl"))
        self._is_loaded = True

    def validate_input(self, input_data):
        required = ["disease", "state", "target_year"]
        return all(k in input_data for k in required)

    def get_feature_names(self):
        return FEATURE_NAMES

    def predict(self, input_data):
        if not self._is_loaded:
            self.load_model()
        disease = input_data.get("disease", "")
        state = input_data.get("state", "")
        target_year = int(input_data.get("target_year", 2025))
        yearly_r0 = input_data.get("yearly_r0", None)
        meta = self._metadata or {}
        d_enc = meta.get("disease_encoding", {}).get(disease, 0)
        s_enc = meta.get("state_encoding", {}).get(state, 0)
        cap = meta.get("state_beds", {}).get(state, {"total_beds": 1000, "hospitals": 10})
        if isinstance(cap, dict):
            state_beds_val = cap.get("total_beds", 1000)
            state_hospitals_val = cap.get("hospitals", 10)
        else:
            state_beds_val, state_hospitals_val = 1000, 10

        disease_defaults = meta.get("disease_defaults", {})
        dd = disease_defaults.get(disease, {"cfr": 1.0, "r0": 2.0})
        cfr_val = dd.get("cfr", 1.0)
        r0_val = dd.get("r0", 2.0)

        # Use per-target-year R₀ if available
        if yearly_r0 and isinstance(yearly_r0, list):
            for entry in yearly_r0:
                if entry.get("year") == target_year:
                    r0_val = entry.get("avg_r0", r0_val)
                    cfr_val = entry.get("avg_cfr", cfr_val)
                    break

        ty_norm = (target_year - 2017) / 15
        feat = np.array([[ty_norm, cfr_val, r0_val, state_beds_val, state_hospitals_val, d_enc, s_enc]])

        try:
            if not self._model or not self._deaths_model:
                raise RuntimeError("ScenarioPredictor models not loaded")
            pred_cases = int(np.expm1(self._model.predict(feat)[0]))
            pred_deaths = int(np.expm1(self._deaths_model.predict(feat)[0]))
        except Exception as e:
            logger.warning(f"ScenarioPredictor failed: {e}")
            raise
        return {
            "total_cases": max(0, pred_cases),
            "total_deaths": max(0, pred_deaths),
            "model": "XGBoost (annual scenario)",
            "is_ml": True,
            "features_used": FEATURE_NAMES,
        }
