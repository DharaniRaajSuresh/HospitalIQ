import pytest

from backend.services.pandemic_service import (
    compute_risk_score,
    generate_recommendations,
    evaluate_lockdown_ml,
)

class TestPandemicService:
    def test_compute_risk_score_no_ml(self):
        totals = {
            "total_confirmed": 10000,
            "total_deaths": 500,
            "avg_r0": 2.5,
            "total_bed_demand": 1500,
            "total_icu_demand": 200,
        }
        # Low risk test case
        score, level, ml_used = compute_risk_score(
            totals={"total_deaths": 10}, target_year=2026, projected_cfr=0.5,
            peak_bed_demand=50, ml_avail=1000, ml_total=2000,
            cur_total=2000, cur_occupancy=50.0, hospital_count=10,
            disease="COVID-19", state="Kerala", risk_predictor=None
        )
        assert level == "low"
        assert score < 30
        assert not ml_used

        # Critical risk test case
        score, level, ml_used = compute_risk_score(
            totals={"total_deaths": 50000}, target_year=2026, projected_cfr=15.0,
            peak_bed_demand=50000, ml_avail=1000, ml_total=2000,
            cur_total=2000, cur_occupancy=90.0, hospital_count=10,
            disease="Ebola", state="Kerala", risk_predictor=None
        )
        assert level == "critical"
        assert score >= 80
        assert not ml_used

    def test_generate_recommendations(self):
        # High severity
        recs = generate_recommendations(
            projected_occupancy=90.0,
            bed_shortage=1000,
            icu_shortage=200,
            projected_cfr=15.0,
            avg_r0=3.5,
            hospitals_at_risk=[{}, {}, {}, {}],  # 4 hospitals
            risk_level="critical",
            state="Kerala",
            target_year=2026,
            lockdown_info={"lockdown_recommended": True, "lockdown_probability": 0.85}
        )
        assert any("activate surge capacity protocols" in r for r in recs)
        assert any("Estimated bed shortage of 1000" in r for r in recs)
        assert any("ICU shortage of 200" in r for r in recs)
        assert any("Projected fatality rate 15.0%" in r for r in recs)
        assert any("High transmissibility (R0=3.5)" in r for r in recs)
        assert any("4 ML-identified hospitals at risk" in r for r in recs)
        assert any("MANDATORY: Lockdown recommended" in r for r in recs)
        assert any("OVERWHELMING: Mass casualty triage" in r for r in recs)

        # Low severity
        recs = generate_recommendations(
            projected_occupancy=50.0,
            bed_shortage=0,
            icu_shortage=0,
            projected_cfr=1.0,
            avg_r0=1.2,
            hospitals_at_risk=[],
            risk_level="low",
            state="Kerala",
            target_year=2026,
            lockdown_info=None
        )
        assert any("Scenario is tolerable for Kerala in 2026" in r for r in recs)

    def test_evaluate_lockdown_ml_fallback(self):
        # When ML is unavailable, deterministic fallback based on R0
        totals = {"avg_r0": 4.0}
        res = evaluate_lockdown_ml(totals, "COVID-19", "Kerala")
        assert res["model"] == "deterministic"
        assert res["is_ml"] is False
        assert res["lockdown_recommended"] is True
        assert res["lockdown_probability"] == 0.8  # min(1.0, 4.0 / 5.0)

        totals = {"avg_r0": 2.0}
        res = evaluate_lockdown_ml(totals, "COVID-19", "Kerala")
        assert res["lockdown_recommended"] is False
        assert res["lockdown_probability"] == 0.4
