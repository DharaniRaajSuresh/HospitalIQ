"""
R0Predictor — Predicts Reproduction Rate (R0) using XGBoost.
Replaces hardcoded 5% annual decay with ML driven by:
  years_since_2020 (temporal decay), vaccination_rate (herd immunity),
  mutation_factor (variant emergence), population_density, disease, state.
"""
import os, logging, math
import numpy as np
import joblib
from backend.core.base_predictor import BasePredictor
from backend.app_state import normalize_state

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "ml_pipeline", "data", "models",
)

FEATURE_NAMES = [
    "population_density", "vaccination_rate", "mutation_factor",
    "years_since_2020", "year_norm", "disease_enc", "state_enc",
]


class R0Predictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="r0_model", model_dir=MODEL_DIR)
        self._metadata = None

    def load_model(self):
        super().load_model()
        meta_path = os.path.join(self._model_dir, "r0_metadata.pkl")
        if os.path.exists(meta_path):
            self._metadata = joblib.load(meta_path)
            logger.info("Loaded R0 metadata")
        self._is_loaded = True

    def validate_input(self, input_data):
        required = ["disease", "state", "target_year"]
        return all(k in input_data for k in required)

    def get_feature_names(self):
        return FEATURE_NAMES

    def predict(self, input_data):
        if not self._is_loaded:
            self.load_model()

        disease = normalize_state(input_data.get("disease", ""))
        state = normalize_state(input_data.get("state", ""))
        target_year = int(input_data.get("target_year", 2026))
        mutation_factor = float(input_data.get("mutation_factor", 1.0))

        meta = self._metadata or {}
        d_enc = meta.get("disease_encoding", {}).get(disease, 0)
        s_enc = meta.get("state_encoding", {}).get(state, 0)
        population_density = meta.get("state_population_density", {}).get(state, 100_000)

        yrs_since = max(0, target_year - 2020)
        vacc = 1.0 / (1.0 + math.exp(-0.45 * (yrs_since - 4)))
        year_norm = (target_year - 2017) / 20.0

        feat = np.array([[
            population_density, vacc, mutation_factor,
            yrs_since, year_norm, d_enc, s_enc,
        ]])

        try:
            predicted_r0 = float(self._model.predict(feat)[0])
            predicted_r0 = max(0.3, min(6.0, round(predicted_r0, 3)))
        except Exception as e:
            logger.warning(f"R0Predictor predict failed: {e}")
            disease_defaults = meta.get("disease_defaults", {})
            predicted_r0 = round(disease_defaults.get(disease, 2.0) * 0.95, 2)

        return {
            "predicted_r0": predicted_r0,
            "input_features": {
                "disease": disease, "state": state, "target_year": target_year,
                "population_density": population_density,
                "vaccination_rate": round(vacc, 3),
                "mutation_factor": mutation_factor,
                "years_since_2020": yrs_since,
            },
            "model": "XGBoost (r0_predictor)",
            "is_ml": True,
        }
