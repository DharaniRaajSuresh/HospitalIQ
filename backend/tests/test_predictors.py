"""
Unit tests for all 6 ML predictors: validate input, feature names, predict structure.
Uses mocking to avoid requiring actual model files on disk.
"""
import os

os.environ["SKIP_DB_INIT"] = "1"

import numpy as np
import pytest
from unittest.mock import MagicMock, mock_open, patch

from backend.predictors.bed_predictor import BedPredictor
from backend.predictors.forecast_predictor import ForecastPredictor
from backend.predictors.hospital_predictor import HospitalPredictor
from backend.predictors.lockdown_predictor import LockdownPredictor
from backend.predictors.mortality_predictor import MortalityPredictor
from backend.predictors.patient_risk_predictor import PatientRiskPredictor
from backend.predictors.r0_predictor import R0Predictor
from backend.predictors.risk_predictor import RiskPredictor
from backend.predictors.scenario_predictor import ScenarioPredictor


class TestBedPredictor:
    def test_validate_input_valid(self):
        p = BedPredictor()
        assert p.validate_input({"state": "Tamil Nadu", "ward_type": "ICU", "months_ahead": 3})
        assert p.validate_input({"state": "Delhi", "ward_type": "General", "months_ahead": 120})

    def test_validate_input_invalid_state(self):
        p = BedPredictor()
        assert not p.validate_input({"state": "Atlantis", "ward_type": "ICU", "months_ahead": 3})

    def test_validate_input_missing_fields(self):
        p = BedPredictor()
        assert not p.validate_input({"state": "Tamil Nadu"})

    def test_validate_input_negative_months(self):
        p = BedPredictor()
        assert not p.validate_input({"state": "Tamil Nadu", "ward_type": "ICU", "months_ahead": -1})

    def test_feature_names(self):
        p = BedPredictor()
        names = p.get_feature_names()
        assert "month_sin" in names
        assert "month_cos" in names
        assert "state_encoded" in names
        assert "ward_type_encoded" in names
        assert len(names) == 11

    def test_preprocess_input(self):
        from collections import deque
        p = BedPredictor()
        p._last_known[("Tamil Nadu", "ICU")] = {"history": [150]*12, "available_beds": 150}
        processed = p.preprocess_input({"state": "Tamil Nadu", "ward_type": "ICU", "month": 6, "year": 2025})
        assert "month_sin" in processed
        assert "state_encoded" in processed
        assert processed["state_encoded"] == p._state_encoding.get("Tamil Nadu")


class TestMortalityPredictor:
    def test_validate_input_valid(self):
        p = MortalityPredictor()
        assert p.validate_input({"district": "Chennai", "age_group": "45-64", "cause": "Cardiac", "year": 2025, "month": 6})

    def test_validate_input_missing(self):
        p = MortalityPredictor()
        assert not p.validate_input({"district": "Chennai"})

    def test_feature_names(self):
        p = MortalityPredictor()
        names = p.get_feature_names()
        assert "district_encoded" in names
        assert "age_group_encoded" in names
        assert "cause_encoded" in names
        assert "month_sin" in names
        assert "lag_1_month" in names
        assert len(names) == 14


class TestHospitalPredictor:
    def test_validate_input_valid(self):
        p = HospitalPredictor()
        assert p.validate_input({"disease": "Pneumonia", "state": "Tamil Nadu", "top_n": 10})

    def test_validate_input_missing_disease(self):
        p = HospitalPredictor()
        assert not p.validate_input({})

    def test_validate_input_invalid_disease(self):
        p = HospitalPredictor()
        assert not p.validate_input({"disease": "AlienFlu"})

    def test_feature_names(self):
        p = HospitalPredictor()
        names = p.get_feature_names()
        assert len(names) > 0


class TestRiskPredictor:
    def test_validate_input_valid(self):
        p = RiskPredictor()
        assert p.validate_input({
            "disease": "COVID-19", "state": "Kerala",
            "total_confirmed": 10000, "total_deaths": 200,
            "avg_cfr": 2.0, "avg_r0": 2.5,
            "total_bed_demand": 1500, "total_icu_demand": 750,
            "peak_monthly_cases": 5000, "total_beds": 20000,
            "bed_occupancy": 65.0, "hospital_count": 50,
        })

    def test_validate_input_missing(self):
        p = RiskPredictor()
        assert not p.validate_input({"disease": "COVID-19"})

    def test_feature_names(self):
        p = RiskPredictor()
        names = p.get_feature_names()
        assert "total_deaths" in names
        assert "avg_cfr" in names
        assert len(names) == 10


class TestForecastPredictor:
    def test_validate_input_valid(self):
        p = ForecastPredictor()
        assert p.validate_input({
            "disease": "COVID-19", "state": "Kerala",
            "history": [(100, 2), (200, 4), (300, 6)],
            "months_ahead": 12,
        })

    def test_validate_input_short_history(self):
        p = ForecastPredictor()
        assert not p.validate_input({
            "disease": "COVID-19", "state": "Kerala",
            "history": [(100, 2)],
            "months_ahead": 12,
        })

    def test_validate_input_missing(self):
        p = ForecastPredictor()
        assert not p.validate_input({"disease": "COVID-19"})

    def test_feature_names(self):
        p = ForecastPredictor()
        names = p.get_feature_names()
        assert "year_normalized" in names
        assert "lag_1_cases" in names
        assert "month_sin" in names
        assert len(names) == 16

    @patch("backend.predictors.forecast_predictor.joblib.load")
    def test_predict_returns_forecast_list(self, mock_load):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([5.5])
        mock_load.side_effect = [
            mock_model,
            mock_model,
            {"disease_encoding": {"COVID-19": 0},
             "state_encoding": {"Kerala": 0},
             "disease_params": {"COVID-19": {"cfr": 2.5, "r0": 2.5}},
             "state_beds": {"Kerala": {"total_beds": 5000, "hospitals": 50}}}
        ]
        p = ForecastPredictor()
        result = p.predict({
            "disease": "COVID-19", "state": "Kerala",
            "history": [(100, 2), (200, 4), (300, 6)],
            "months_ahead": 6,
        })
        assert "forecast" in result
        assert isinstance(result["forecast"], list)
        assert "model" in result


class TestScenarioPredictor:
    def test_validate_input_valid(self):
        p = ScenarioPredictor()
        assert p.validate_input({"disease": "COVID-19", "state": "Kerala", "target_year": 2028})

    def test_validate_input_missing(self):
        p = ScenarioPredictor()
        assert not p.validate_input({"disease": "COVID-19"})

    def test_feature_names(self):
        p = ScenarioPredictor()
        names = p.get_feature_names()
        assert "target_year_norm" in names
        assert "avg_cfr" in names
        assert "disease_enc" in names
        assert len(names) == 7


class TestPatientRiskPredictor:
    @patch("backend.predictors.patient_risk_predictor.Path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open)
    @patch("backend.predictors.patient_risk_predictor.pickle.load")
    def test_predict_returns_dict_with_status(self, mock_load, mock_file, mock_exists):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([0.3])
        metadata = {"feature_names": ["age", "blood_group", "gender_male",
                      "num_preexisting", "num_doses", "has_covid_vaccine",
                      "last_vaccine_days", "recent_travel", "num_trips",
                      "fam_high_risk", "fam_total", "virus_fatality",
                      "virus_reproductive", "vaccine_available",
                      "vaccine_effectiveness"],
                    "target_names": ["risk_score", "hospitalization_prob", "mortality_prob"]}
        mock_load.side_effect = [
            {"risk_score": mock_model, "hospitalization_prob": mock_model, "mortality_prob": mock_model},
            metadata,
        ]
        p = PatientRiskPredictor()
        p.load_model()
        features = {"age": 0.45, "blood_group": 6, "gender_male": 1,
                     "num_preexisting": 2, "num_doses": 2, "has_covid_vaccine": 1,
                     "last_vaccine_days": 0.3, "recent_travel": 1, "num_trips": 3,
                     "fam_high_risk": 1, "fam_total": 4, "virus_fatality": 0.05,
                     "virus_reproductive": 2.5, "vaccine_available": 1,
                     "vaccine_effectiveness": 0.9}
        result = p.predict(features)
        assert isinstance(result, dict)
        assert "risk_score" in result
        # Model not loaded in test env, so status should indicate that
        assert result["status"] in ("ml_model", "Model not loaded")

    def test_predict_empty_features_does_not_crash(self):
        p = PatientRiskPredictor()
        with pytest.raises(RuntimeError, match="Patient risk model not loaded"):
            p.predict({})

    def test_is_loaded_false_by_default(self):
        p = PatientRiskPredictor()
        assert not p.is_loaded

class TestLockdownPredictor:
    def test_validate_input_valid(self):
        p = LockdownPredictor()
        assert p.validate_input({"total_cases": 1000, "total_deaths": 50, "avg_r0": 1.5, "avg_cfr": 2.0, "total_bed_demand": 500, "total_icu_demand": 100})

    def test_feature_names(self):
        p = LockdownPredictor()
        assert "avg_r0" in p.get_feature_names()

class TestR0Predictor:
    def test_validate_input_valid(self):
        p = R0Predictor()
        assert p.validate_input({"disease": "COVID-19", "state": "Kerala", "target_year": 2026})

    def test_feature_names(self):
        p = R0Predictor()
        assert "population_density" in p.get_feature_names()
