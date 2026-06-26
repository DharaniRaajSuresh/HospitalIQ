"""
backend/predictors/risk_predictor.py - Pandemic risk scoring via direct formula.
The risk score is a deterministic composite of death severity, system overwhelm,
and CFR — no ML model needed. This replaces the previous RandomForest that
was learning back its own synthetic training labels (R² 0.99, meaningless).
"""

import numpy as np

from backend.core.base_predictor import BasePredictor

FEATURE_NAMES = [
    "total_confirmed", "total_deaths", "avg_cfr", "avg_r0",
    "total_bed_demand", "total_icu_demand", "peak_monthly_cases",
    "total_beds", "bed_occupancy", "hospital_count",
]


class RiskPredictor(BasePredictor):
    def __init__(self):
        super().__init__(model_name="risk_model")

    def load_model(self):
        self._is_loaded = True

    def validate_input(self, input_data):
        required = ["disease", "state", "total_confirmed", "total_deaths",
                     "avg_cfr", "avg_r0", "total_bed_demand", "total_icu_demand",
                     "peak_monthly_cases", "total_beds", "bed_occupancy", "hospital_count"]
        for key in required:
            if key not in input_data:
                return False
        return True

    def get_feature_names(self):
        return FEATURE_NAMES

    def predict(self, input_data):
        if not self.validate_input(input_data):
            return {"risk_score": None, "risk_level": None,
                    "error": "Invalid input", "model": "risk_formula", "is_ml": False}

        try:
            total_deaths = int(input_data.get("total_deaths", 0))
            total_bed_demand = int(input_data.get("total_bed_demand", 0))
            total_beds = int(input_data.get("total_beds", 1))
            avg_cfr = float(input_data.get("avg_cfr", 0))

            # Death severity component (0-60)
            death_sev = min(60, int(np.log10(max(total_deaths, 1)) * 15 - 5)) if total_deaths > 0 else 0

            # System overwhelm component (0-40)
            ratio = total_bed_demand / max(total_beds, 1)
            overwhelm_sev = min(40, int(np.log10(max(ratio, 1)) * 20))

            # CFR bonus (0-15)
            cfr_bonus = min(15, int(avg_cfr / 5))

            score = max(0, min(100, death_sev + overwhelm_sev + cfr_bonus))

            if score < 30:
                level = "low"
            elif score < 55:
                level = "moderate"
            elif score < 80:
                level = "high"
            else:
                level = "critical"

            return {
                "risk_score": score,
                "risk_level": level,
                "model": "risk_formula",
                "is_ml": False,
                "components": {
                    "death_severity": death_sev,
                    "overwhelm_severity": overwhelm_sev,
                    "cfr_bonus": cfr_bonus,
                },
            }
        except Exception as e:
            return {"risk_score": None, "risk_level": None,
                    "error": str(e), "model": "risk_formula", "is_ml": False}
