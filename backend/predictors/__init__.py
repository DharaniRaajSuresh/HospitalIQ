"""
backend/predictors/__init__.py - Export concrete predictors
"""

from backend.predictors.bed_predictor import BedPredictor
from backend.predictors.forecast_predictor import ForecastPredictor
from backend.predictors.hospital_predictor import HospitalPredictor
from backend.predictors.mortality_predictor import MortalityPredictor
from backend.predictors.r0_predictor import R0Predictor
from backend.predictors.risk_predictor import RiskPredictor
from backend.predictors.scenario_predictor import ScenarioPredictor

__all__ = [
    "BedPredictor",
    "MortalityPredictor",
    "HospitalPredictor",
    "RiskPredictor",
    "ForecastPredictor",
    "ScenarioPredictor",
    "R0Predictor",
]
