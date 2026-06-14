"""Personalized patient pandemic risk predictor."""
import pickle
import logging
from datetime import datetime, timezone
import numpy as np
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent.parent / "ml_pipeline" / "data" / "models"
MODEL_NAME = "patient_risk_model"


class PatientRiskPredictor:
    def __init__(self):
        self._models = None
        self._metadata = None
        self._is_loaded = False

    def load_model(self):
        model_path = MODEL_DIR / "patient_risk_model.pkl"
        meta_path = MODEL_DIR / "patient_risk_metadata.pkl"
        if not model_path.exists():
            logger.warning(f"Patient risk model not found at {model_path}")
            return
        with open(model_path, "rb") as f:
            self._models = pickle.load(f)
        with open(meta_path, "rb") as f:
            self._metadata = pickle.load(f)
        self._is_loaded = True
        self._load_timestamp = datetime.now(timezone.utc).isoformat()
        logger.info("Loaded patient risk predictor")

    @property
    def is_loaded(self):
        return self._is_loaded

    def get_model_info(self):
        return {
            "model_name": MODEL_NAME,
            "is_loaded": self._is_loaded,
            "load_timestamp": str(getattr(self, "_load_timestamp", None)),
            "model_path": str(MODEL_DIR / f"{MODEL_NAME}.pkl"),
        }

    def predict(self, features: dict[str, Any]) -> dict[str, Any]:
        if not self._is_loaded:
            return {"status": "ml_model", "error": "Model not loaded"}
        
        feature_names = self._metadata["feature_names"]
        row = []
        for fn in feature_names:
            row.append(features.get(fn, 0.0))
        
        X = np.array([row], dtype=np.float32)
        
        result = {}
        for target in self._metadata["target_names"]:
            pred = self._models[target].predict(X)[0]
            result[target] = round(float(pred), 4)
            result[f"{target}_pct"] = round(float(pred) * 100, 1)
        
        # Risk level
        rs = result["risk_score"]
        if rs < 0.2:
            result["risk_level"] = "Low"
        elif rs < 0.4:
            result["risk_level"] = "Moderate"
        elif rs < 0.6:
            result["risk_level"] = "Elevated"
        elif rs < 0.8:
            result["risk_level"] = "High"
        else:
            result["risk_level"] = "Critical"
        
        result["status"] = "ml_model"
        return result
