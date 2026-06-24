import os, logging
import numpy as np
import joblib
from backend.core.base_predictor import BasePredictor

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)

FEATURE_NAMES = ["avg_r0", "avg_cfr", "total_cases", "total_deaths", "total_bed_demand", "total_icu_demand", "disease_enc", "state_enc"]


class LockdownPredictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="lockdown_model", model_dir=MODEL_DIR)
        self._scaler = None

    def load_model(self):
        self._model = joblib.load(os.path.join(self._model_dir, "lockdown_model.pkl"))
        scaler_path = os.path.join(self._model_dir, "lockdown_scaler.pkl")
        if os.path.exists(scaler_path):
            self._scaler = joblib.load(scaler_path)
        self._is_loaded = True
        logger.info("Loaded LockdownPredictor")

    def validate_input(self, input_data):
        return all(k in input_data for k in ["total_cases", "total_deaths", "avg_r0"])

    def get_feature_names(self):
        return FEATURE_NAMES

    def predict(self, input_data):
        if not self._is_loaded:
            self.load_model()
        feat = np.array([[input_data.get(k, 0) for k in FEATURE_NAMES]])
        if self._scaler:
            feat = self._scaler.transform(feat)
        proba = float(self._model.predict_proba(feat)[0, 1])
        pred = int(self._model.predict(feat)[0])
        return {
            "lockdown_probability": round(proba, 3),
            "lockdown_recommended": bool(pred),
            "model": "XGBoost (lockdown classifier)",
            "is_ml": True,
        }
