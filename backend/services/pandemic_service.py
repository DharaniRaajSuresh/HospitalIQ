"""Pandemic scenario service — clean business logic extracted from the 303-line router."""
import logging

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app_state import loaded_predictors, normalize_state
from backend.models import HospitalBed, HospitalOutcome, PandemicOutbreak

logger = logging.getLogger(__name__)

DISEASE_INFO = {
    "COVID-19": {"type": "Coronavirus", "cfr": "1-5%", "r0": "2.5-4.0"},
    "Ebola": {"type": "Viral Hemorrhagic Fever", "cfr": "50-90%", "r0": "1.5-2.0"},
    "H1N1": {"type": "Pandemic Influenza", "cfr": "0.1-2%", "r0": "1.4-1.8"},
    "SARS": {"type": "Coronavirus", "cfr": "10-15%", "r0": "2.0-3.5"},
    "Nipah": {"type": "Henipavirus", "cfr": "40-75%", "r0": "1.2-1.7"},
    "Marburg": {"type": "Viral Hemorrhagic Fever", "cfr": "24-88%", "r0": "1.5-2.0"},
}
DISEASE_DEFAULT_R0 = {
    "COVID-19": 3.25, "Ebola": 1.75, "H1N1": 1.6, "SARS": 2.75, "Nipah": 1.45, "Marburg": 1.75,
}
DISEASE_TO_CAUSE = {"COVID-19": "Respiratory", "Ebola": "Infectious", "H1N1": "Respiratory",
                     "SARS": "Respiratory", "Nipah": "Infectious", "Marburg": "Infectious"}
DISEASE_MAP = {"COVID-19": "Pneumonia", "H1N1": "Pneumonia", "SARS": "Pneumonia"}
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_outbreak_totals(disease: str, state: str | None, db: Session) -> dict:
    q = db.query(
        func.sum(PandemicOutbreak.confirmed_cases), func.sum(PandemicOutbreak.deaths),
        func.sum(PandemicOutbreak.recovered), func.sum(PandemicOutbreak.active_cases),
        func.sum(PandemicOutbreak.bed_demand), func.sum(PandemicOutbreak.icu_demand),
        func.sum(PandemicOutbreak.ventilator_demand), func.avg(PandemicOutbreak.reproduction_rate),
        func.avg(PandemicOutbreak.case_fatality_rate),
    ).filter(PandemicOutbreak.disease == disease)
    if state:
        q = q.filter(PandemicOutbreak.state == state)
    od = q.first()
    if not od:
        return {}
    return {
        "total_confirmed": int(od[0] or 0), "total_deaths": int(od[1] or 0),
        "total_recovered": int(od[2] or 0), "total_active": int(od[3] or 0),
        "total_bed_demand": int(od[4] or 0), "total_icu_demand": int(od[5] or 0),
        "total_vent_demand": int(od[6] or 0), "avg_r0": round(float(od[7] or 0), 2),
        "avg_cfr": round(float(od[8] or 0), 2),
    }


def fetch_monthly_series(disease: str, state: str | None, db: Session) -> list[dict]:
    q = db.query(
        PandemicOutbreak.year, PandemicOutbreak.month,
        func.sum(PandemicOutbreak.confirmed_cases), func.sum(PandemicOutbreak.deaths),
        func.sum(PandemicOutbreak.recovered), func.sum(PandemicOutbreak.bed_demand),
        func.sum(PandemicOutbreak.icu_demand),
    ).filter(PandemicOutbreak.disease == disease)
    if state:
        q = q.filter(PandemicOutbreak.state == state)
    rows = q.group_by(PandemicOutbreak.year, PandemicOutbreak.month).order_by(
        PandemicOutbreak.year, PandemicOutbreak.month).all()
    return [
        {"month": f"{MONTH_NAMES[r.month-1]} {r.year}", "year": r.year, "month_num": r.month,
         "confirmed_cases": int(r[2] or 0), "deaths": int(r[3] or 0),
         "recovered": int(r[4] or 0), "bed_demand": int(r[5] or 0), "icu_demand": int(r[6] or 0)}
        for r in rows
    ]


def fetch_capacity(state: str | None, db: Session) -> dict:
    bf = [HospitalBed.state == state] if state else []
    subq = db.query(HospitalBed.hospital_name, HospitalBed.ward_type,
                    func.max(HospitalBed.total_beds).label("max_beds"),
                    func.max(HospitalBed.available_beds).label("max_avail"),
                    ).filter(*bf).group_by(HospitalBed.hospital_name, HospitalBed.ward_type).subquery()
    cr = db.query(func.sum(subq.c.max_beds), func.sum(subq.c.max_avail)).first()
    cur_total, cur_available = int(cr[0] or 0), int(cr[1] or 0)
    hospital_count = int(
        db.query(func.count(HospitalBed.hospital_name.distinct())).filter(*bf).first()[0] or 0)
    cur_occupancy = float(
        db.query(func.avg(HospitalBed.occupancy_rate)).filter(*bf).first()[0] or 0)
    icu_q = db.query(func.sum(HospitalOutcome.icu_beds))
    if state:
        icu_q = icu_q.filter(HospitalOutcome.state == state)
    total_icu_capacity = int(icu_q.scalar() or 0) or int(cur_total * 0.15)
    return {
        "total": cur_total, "available": cur_available, "occupancy": cur_occupancy,
        "icu": total_icu_capacity, "hospitals": hospital_count,
    }


def predict_beds(state: str | None, target_year: int, cap: dict,
                 bed_predictor) -> tuple[int, int, int]:
    if not (bed_predictor and getattr(bed_predictor, "_is_loaded", False) and state):
        return cap["total"], cap["icu"], cap["available"]
    ml_total = ml_icu = 0
    for ward in ["General", "ICU", "Emergency", "Maternity"]:
        try:
            result = bed_predictor.predict({
                "state": state, "ward_type": ward,
                "months_ahead": max(1, min(120, 6 + (target_year - 2026) * 12)),
            })
            forecasts = result.get("forecast", [])
            if forecasts:
                beds = forecasts[-1]["predicted_beds"] * max(1, cap["hospitals"])
                ml_total += beds
                if ward == "ICU":
                    ml_icu = beds
        except Exception as e:
            logger.warning(f"BedPredictor {ward}: {e}")
    return int(ml_total), int(ml_icu), max(0, int(ml_total * (1 - cap["occupancy"] / 100)))


def predict_mortality(state: str | None, disease: str, target_year: int, db: Session,
                      mortality_predictor) -> float | None:
    cause = DISEASE_TO_CAUSE.get(disease, "Other")
    if not (mortality_predictor and getattr(mortality_predictor, "_is_loaded", False) and state and cause != "Other"):
        return None
    districts = [d for d, s in getattr(mortality_predictor, "_district_to_state", {}).items() if s == state]
    if not districts:
        return None
    try:
        mr = mortality_predictor.predict({
            "district": districts[0], "age_group": "45-64",
            "cause": cause, "year": min(target_year, 2036), "month": 6,
        })
        return mr.get("predicted_death_rate", 0)
    except Exception as e:
        logger.warning(f"MortalityPredictor: {e}")
        return None


def predict_hospital_risk(disease: str, state: str | None, db: Session,
                          hospital_predictor) -> list[dict]:
    mapped = DISEASE_MAP.get(disease)
    if hospital_predictor and getattr(hospital_predictor, "_is_loaded", False) and mapped:
        try:
            rankings = hospital_predictor.predict({
                "disease": mapped, "state": state, "top_n": 20,
            }).get("rankings", [])
            hospitals = sorted(rankings, key=lambda x: x.get("hospital_score", 0))[:10]
            if hospitals:
                return [
                    {"name": h.get("hospital_name"), "district": h.get("district"),
                     "beds": h.get("total_beds", 0), "type": h.get("hospital_type"),
                     "icu_beds": h.get("icu_beds", 0), "specialists": h.get("specialist_count", 0)}
                    for h in hospitals
                ]
        except Exception as e:
            logger.warning(f"HospitalPredictor: {e}")
    q = db.query(HospitalOutcome.hospital_name, HospitalOutcome.district,
                 HospitalOutcome.total_beds, HospitalOutcome.hospital_type,
                 HospitalOutcome.icu_beds, HospitalOutcome.specialist_count)
    if state:
        q = q.filter(HospitalOutcome.state == state)
    return [
        {"name": r.hospital_name, "district": r.district, "beds": r.total_beds or 0,
         "type": r.hospital_type, "icu_beds": r.icu_beds or 0, "specialists": r.specialist_count or 0}
        for r in q.filter(HospitalOutcome.total_beds < 50).distinct().limit(10).all()
    ]


def compute_projections(monthly: list[dict], target_year: int, max_data_year: int,
                        disease: str, state: str | None, totals: dict, ml_total: int,
                        cur_total: int, ml_icu: int, cur_occupancy: float, avg_cfr: float,
                        forecast_predictor, scenario_predictor=None) -> list[dict]:
    projected = list(monthly)
    if target_year <= max_data_year or not monthly or totals.get("total_confirmed", 0) <= 0:
        return [m for m in projected if m["year"] == target_year] if target_year <= max_data_year else projected

    if forecast_predictor and getattr(forecast_predictor, "_is_loaded", False) and state:
        try:
            sorted_m = sorted(monthly, key=lambda x: (x["year"], x["month_num"]))
            months_needed = max(24, (target_year - max_data_year) * 12 + 12)
            ml_forecast = forecast_predictor.predict({
                "disease": disease, "state": state,
                "history": [(m["confirmed_cases"], m["deaths"]) for m in sorted_m[-3:]],
                "months_ahead": months_needed,
                "start_year_month": [sorted_m[-1]["year"], sorted_m[-1]["month_num"]],
            })
            for m in ml_forecast.get("forecast", []):
                if "month_num" not in m and "month" in m:
                    m["month_num"] = m["month"]
            projected.extend(ml_forecast.get("forecast", []))
            projected.sort(key=lambda x: (x["year"], x["month_num"]))

            # Scale forecast monthly distribution to scenario model's annual magnitude
            # (uses scenario model's year total, keeps forecast model's monthly pattern)
            if scenario_predictor and getattr(scenario_predictor, "_is_loaded", False):
                try:
                    scenario = scenario_predictor.predict({
                        "disease": disease, "state": state, "target_year": target_year,
                        "yearly_r0": None,
                    })
                    if scenario.get("is_ml"):
                        target_annual = scenario["total_cases"]
                        forecast_months = [m for m in projected if m["year"] == target_year and m.get("projected")]
                        forecast_total = sum(m["confirmed_cases"] for m in forecast_months)
                        if forecast_total > 0 and target_annual > 0:
                            scale = target_annual / forecast_total
                            for m in projected:
                                if m.get("projected"):
                                    m["confirmed_cases"] = int(m["confirmed_cases"] * scale)
                                    m["deaths"] = int(m["deaths"] * scale)
                                    m["recovered"] = m["confirmed_cases"] - m["deaths"]
                            logger.info(f"Scenario scale={scale:.2f} (target={target_annual}, forecast_total={forecast_total})")
                except Exception as e2:
                    logger.warning(f"Scenario scaling failed: {e2}")

            return projected
        except Exception as e:
            logger.warning(f"ML forecast failed: {e}")

    logger.warning("ML forecast unavailable, returning historical data only")
    return projected


def compute_risk_score(totals: dict, target_year: int, projected_cfr: float,
                       peak_bed_demand: int, ml_avail: int, ml_total: int,
                       cur_total: int, cur_occupancy: float, hospital_count: int,
                       disease: str, state: str | None, risk_predictor) -> tuple[float, str, bool]:
    risk_input = {
        "disease": disease, "state": state or "", "total_confirmed": totals.get("total_confirmed", 0),
        "total_deaths": totals.get("total_deaths", 0), "avg_cfr": projected_cfr,
        "avg_r0": totals.get("avg_r0", 0), "total_bed_demand": totals.get("total_bed_demand", 0),
        "total_icu_demand": totals.get("total_icu_demand", 0),
        "peak_monthly_cases": totals.get("total_confirmed", 0),
        "total_beds": ml_total if state else cur_total,
        "bed_occupancy": cur_occupancy, "hospital_count": hospital_count,
    }
    ml_used = False
    if risk_predictor and getattr(risk_predictor, "_is_loaded", False) and state:
        try:
            pred = risk_predictor.predict(risk_input)
            return (pred.get("risk_score") or 0, pred.get("risk_level") or "moderate", True)
        except Exception as e:
            logger.warning("Risk prediction in pandemic service failed: %s", e)
    deaths = totals.get("total_deaths", 0)
    score = min(100, int((deaths ** 0.5) * 0.5) + min(20, int(projected_cfr / 2.5)) + min(10, int(max(0, peak_bed_demand - ml_avail) / max(peak_bed_demand, 1) * 10)))
    level = "low" if score < 30 else "moderate" if score < 55 else "high" if score < 80 else "critical"
    return (score, level, ml_used)


def fetch_yearly_r0(disease: str, state: str | None, db: Session) -> list[dict]:
    q = db.query(
        PandemicOutbreak.year,
        func.avg(PandemicOutbreak.reproduction_rate),
        func.avg(PandemicOutbreak.case_fatality_rate),
        func.sum(PandemicOutbreak.confirmed_cases),
    ).filter(PandemicOutbreak.disease == disease)
    if state:
        q = q.filter(PandemicOutbreak.state == state)
    rows = q.group_by(PandemicOutbreak.year).order_by(PandemicOutbreak.year).all()
    return [
        {"year": r[0], "avg_r0": round(float(r[1] or 0), 2),
         "avg_cfr": round(float(r[2] or 0), 2), "total_cases": int(r[3] or 0)}
        for r in rows
    ]


def evaluate_lockdown_ml(totals: dict, disease: str, state: str | None) -> dict:
    lockdown_predictor = loaded_predictors.get("lockdown")
    if lockdown_predictor and getattr(lockdown_predictor, "_is_loaded", False) and state:
        try:
            return lockdown_predictor.predict({
                "avg_r0": totals.get("avg_r0", 0),
                "avg_cfr": totals.get("avg_cfr", 0),
                "total_cases": totals.get("total_confirmed", 0),
                "total_deaths": totals.get("total_deaths", 0),
                "total_bed_demand": totals.get("total_bed_demand", 0),
                "total_icu_demand": totals.get("total_icu_demand", 0),
            })
        except Exception as e:
            logger.warning(f"Lockdown ML failed: {e}")
    r0 = totals.get("avg_r0", 0)
    return {"lockdown_probability": round(min(1.0, r0 / 5.0), 3), "lockdown_recommended": r0 > 3.5, "model": "deterministic", "is_ml": False}


def generate_recommendations(projected_occupancy: float, bed_shortage: int, icu_shortage: int,
                             projected_cfr: float, avg_r0: float, hospitals_at_risk: list,
                             risk_level: str, state: str | None, target_year: int,
                             lockdown_info: dict | None = None) -> list[str]:
    recs = []
    if projected_occupancy > 85:
        recs.append(f"Bed occupancy may hit {projected_occupancy}% in {target_year} — activate surge capacity protocols")
    if bed_shortage > 0:
        recs.append(f"Estimated bed shortage of {bed_shortage} in peak month — consider temporary facilities")
    if icu_shortage > 0:
        recs.append(f"ICU shortage of {icu_shortage} beds — ICU demand exceeds capacity")
    if projected_cfr > 10:
        recs.append(f"Projected fatality rate {projected_cfr}% — escalate ICU capacity")
    if avg_r0 > 2:
        recs.append(f"High transmissibility (R0={avg_r0}) — strict containment measures recommended")
    if len(hospitals_at_risk) > 3:
        recs.append(f"{len(hospitals_at_risk)} ML-identified hospitals at risk — prioritize resource allocation")
    if lockdown_info and lockdown_info.get("lockdown_recommended"):
        prob = lockdown_info.get("lockdown_probability", 0) * 100
        recs.append(f"MANDATORY: Lockdown recommended ({prob:.0f}% confidence) — initiate immediately")
    elif lockdown_info and lockdown_info.get("lockdown_probability", 0) > 0.5:
        prob = lockdown_info.get("lockdown_probability", 0) * 100
        recs.append(f"ADVISORY: Prepare for potential lockdown ({prob:.0f}% probability)")
    if risk_level in ("high", "critical"):
        msg = "CRITICAL: Emergency protocols must be activated before outbreak peak" if risk_level == "high" else "OVERWHELMING: Mass casualty triage, patient evacuation, and field hospitals required"
        recs.append(msg)
    elif risk_level == "moderate":
        recs.append("Partial capacity strain expected — pre-position medical supplies")
    else:
        recs.append(f"Scenario is tolerable for {state or 'India'} in {target_year} — continue monitoring")
    return recs


def build_scenario(disease: str, state: str | None, target_year: int, db: Session,
                  manual_r0: float | None = None) -> dict:
    if state:
        state = normalize_state(state)

    totals = fetch_outbreak_totals(disease, state, db)
    monthly = fetch_monthly_series(disease, state, db)
    cap = fetch_capacity(state, db)
    yearly_r0_data = fetch_yearly_r0(disease, state, db)

    if not monthly:
        raise ValueError(f"No monthly outbreak data for {disease}/{state}")
    min_year = min(m["year"] for m in monthly)
    max_data_year = max(m["year"] for m in monthly)
    target_year = min(max(target_year if target_year else max_data_year, min_year), 2040)

    if manual_r0 is not None:
        manual_r0 = max(0.1, min(10.0, round(float(manual_r0), 2)))
        default_r0 = DISEASE_DEFAULT_R0.get(disease, 2.0)
        scale = manual_r0 / default_r0
        scaled = lambda v: int((v or 0) * scale)
        sc = scaled(totals.get("total_confirmed") or 0)
        sd = scaled(totals.get("total_deaths") or 0)
        cfr = round(sd / max(sc, 1) * 100, 2) if sc else 0
        risk_score = min(100, int(manual_r0 / default_r0 * 50))
        risk_level = "low" if risk_score < 30 else "moderate" if risk_score < 55 else "high" if risk_score < 80 else "critical"
        verdict = "Tolerable" if risk_score < 30 else "Concerning" if risk_score < 55 else "Critical" if risk_score < 80 else "Overwhelming"
        lockdown = risk_score > 75
        recs = []
        if manual_r0 > 2:
            recs.append(f"High transmissibility (R0={manual_r0}) — strict containment measures recommended")
        if lockdown:
            recs.append("MANDATORY: Lockdown recommended — initiate immediately")
        if risk_level in ("high", "critical"):
            recs.append("CRITICAL: Emergency protocols must be activated")
        elif risk_level == "moderate":
            recs.append("Partial capacity strain expected — pre-position medical supplies")
        else:
            recs.append(f"Scenario is tolerable for {state or 'India'} — continue monitoring")
        return {
            "disease": disease, "disease_info": DISEASE_INFO.get(disease, {}),
            "state": state or "All India", "projection_year": target_year,
            "scenario": {"predicted_peak_demand": 0, "predicted_cfr": cfr, "forecast_months": 0, "data_source": "manual_r0",
                "ml_models_used": {k: False for k in ["bed_predictor","mortality_predictor","hospital_predictor","forecast_predictor","risk_predictor","scenario_predictor","r0_predictor"]}},
            "outbreak_summary": {
                "total_confirmed_cases": sc, "total_deaths": sd, "total_recovered": scaled(totals.get("total_recovered") or 0),
                "total_active_cases": scaled(totals.get("total_active") or 0),
                "total_bed_demand": scaled(totals.get("total_bed_demand") or 0),
                "total_icu_demand": scaled(totals.get("total_icu_demand") or 0),
                "total_ventilator_demand": scaled(totals.get("total_vent_demand") or 0),
                "avg_reproduction_rate": manual_r0, "avg_case_fatality_rate": cfr,
            },
            "current_capacity": {"bed_occupancy": round(cap["occupancy"], 1), "available_beds": cap["available"],
                "total_beds": cap["total"], "icu_capacity": cap["icu"], "hospitals": cap["hospitals"]},
            "ml_predicted_capacity": {"predicted_total_beds": 0, "predicted_icu_beds": 0, "predicted_available_beds": 0,
                "model": "manual_r0", "ml_death_rate_per_100k": None, "ml_model": "manual_r0"},
            "projected_impact": {"bed_occupancy": round(cap["occupancy"], 1), "available_beds": cap["available"],
                "bed_shortage": 0, "icu_shortage": 0, "projected_deaths": sd, "projected_cfr": cfr,
                "projected_bed_demand": scaled(totals.get("total_bed_demand") or 0),
                "projected_icu_demand": scaled(totals.get("total_icu_demand") or 0)},
            "tolerability": {"risk_score": risk_score, "risk_level": risk_level, "verdict": verdict,
                "bed_occupancy_risk": 0, "fatality_risk": 0, "icu_capacity_risk": 0, "bed_demand_risk": 0},
            "monthly_breakdown": [], "hospitals_at_risk": [],
            "recommendations": recs,
            "recommendations_detailed": [{"priority": i+1, "message": r, "category": "containment" if "containment" in r.lower() else "lockdown" if "lockdown" in r.lower() else "alert"} for i, r in enumerate(recs)],
            "lockdown_recommended": lockdown, "yearly_r0_trend": [], "r0_source": "manual",
        }
    else:
        target_r0 = totals.get("avg_r0", 0)
        for entry in yearly_r0_data:
            if entry["year"] == target_year:
                target_r0 = entry["avg_r0"]
                break
        else:
            if yearly_r0_data:
                last_entry = yearly_r0_data[-1]
                if target_year > last_entry["year"]:
                    r0_predictor = loaded_predictors.get("r0")
                    if r0_predictor and getattr(r0_predictor, "_is_loaded", False) and state:
                        try:
                            result = r0_predictor.predict({
                                "disease": disease, "state": state, "target_year": target_year,
                            })
                            target_r0 = result.get("predicted_r0", last_entry["avg_r0"])
                        except Exception as e:
                            logger.warning(f"R0Predictor failed: {e}")
                            target_r0 = last_entry["avg_r0"]
                    else:
                        target_r0 = last_entry["avg_r0"]
                else:
                    target_r0 = last_entry["avg_r0"]

    totals["avg_r0"] = target_r0

    min_year = min(m["year"] for m in monthly)
    max_data_year = max(m["year"] for m in monthly)
    target_year = min(max(target_year if target_year else max_data_year, min_year), 2040)

    bed_predictor = loaded_predictors.get("bed")
    ml_total, ml_icu, ml_avail = predict_beds(state, target_year, cap, bed_predictor)

    mortality_predictor = loaded_predictors.get("mortality")
    ml_death_rate = predict_mortality(state, disease, target_year, db, mortality_predictor)

    avg_cfr = totals.get("avg_cfr", 0)
    hospital_predictor = loaded_predictors.get("hospital")
    hospitals_at_risk = predict_hospital_risk(disease, state, db, hospital_predictor)

    forecast_predictor = loaded_predictors.get("forecast")
    scenario_predictor = loaded_predictors.get("scenario")
    projected_monthly = compute_projections(monthly, target_year, max_data_year, disease, state,
                                            totals, ml_total, cap["total"], ml_icu, cap["occupancy"],
                                            avg_cfr, forecast_predictor, scenario_predictor)

    year_entries = [m for m in projected_monthly if m["year"] == target_year]
    if year_entries:
        totals = {
            "total_confirmed": sum(m["confirmed_cases"] for m in year_entries),
            "total_deaths": sum(m["deaths"] for m in year_entries),
            "total_recovered": sum(m["recovered"] for m in year_entries),
            "total_active": sum(m["confirmed_cases"] for m in year_entries) - sum(m["deaths"] for m in year_entries) - sum(m["recovered"] for m in year_entries),
            "total_bed_demand": sum(m["bed_demand"] for m in year_entries),
            "total_icu_demand": sum(m["icu_demand"] for m in year_entries),
            "total_vent_demand": int(sum(m["bed_demand"] for m in year_entries) * 0.3),  # heuristic: ~30% of bed cases need ventilation
            "avg_r0": target_r0,
            "avg_cfr": round(sum(m["deaths"] for m in year_entries) / max(sum(m["confirmed_cases"] for m in year_entries), 1) * 100, 2) if year_entries else 0,
        }

    peak_entry = max(year_entries, key=lambda x: x["confirmed_cases"]) if year_entries else None
    peak_bed_demand = peak_entry["bed_demand"] if peak_entry else 0
    peak_icu_demand = peak_entry["icu_demand"] if peak_entry else 0
    total_year_deaths = sum(m["deaths"] for m in year_entries) if year_entries else 0
    projected_occupancy = min(99.9, round(((cap["occupancy"] / 100 * cap["total"]) + peak_bed_demand) / max(cap["total"] + peak_bed_demand, 1) * 100, 1))
    bed_shortage = max(0, int(peak_bed_demand - ml_avail))
    icu_shortage = max(0, int(peak_icu_demand - ml_icu))

    risk_predictor = loaded_predictors.get("risk")
    risk_score, risk_level, ml_risk = compute_risk_score(
        totals, target_year, totals.get("avg_cfr", 0), peak_bed_demand, ml_avail,
        ml_total, cap["total"], cap["occupancy"], cap["hospitals"], disease, state, risk_predictor)

    verdicts = {"low": "Tolerable", "moderate": "Concerning", "high": "Critical", "critical": "Overwhelming"}
    verdict = verdicts.get(risk_level, "Unknown") if ml_risk else (
        "Tolerable" if risk_score < 30 else "Concerning" if risk_score < 55 else "Critical" if risk_score < 80 else "Overwhelming")

    # Lockdown aligned with risk level: high/critical risk → lockdown
    if risk_level in ("high", "critical"):
        lockdown_info = {"lockdown_probability": 1.0, "lockdown_recommended": True, "model": "risk-level-based", "is_ml": False}
    else:
        lockdown_info = {"lockdown_probability": 0, "lockdown_recommended": False, "model": "risk-level-based", "is_ml": False}

    recommendations = generate_recommendations(projected_occupancy, bed_shortage, icu_shortage,
                                                totals.get("avg_cfr", 0), totals.get("avg_r0", 0),
                                                hospitals_at_risk, risk_level, state, target_year,
                                                lockdown_info)

    return {
        "disease": disease, "disease_info": DISEASE_INFO.get(disease, {}),
        "state": state or "All India", "projection_year": target_year,
        "scenario": {
            "predicted_peak_demand": peak_bed_demand,
            "predicted_cfr": totals.get("avg_cfr", 0),
            "forecast_months": len(projected_monthly),
            "data_source": "real_data" if disease == "COVID-19" else "who_parameterized",
            "ml_models_used": {
                "bed_predictor": bool(bed_predictor and getattr(bed_predictor, "_is_loaded", False)),
                "mortality_predictor": bool(mortality_predictor and getattr(mortality_predictor, "_is_loaded", False)),
                "hospital_predictor": bool(hospital_predictor and getattr(hospital_predictor, "_is_loaded", False)),
                "forecast_predictor": bool(forecast_predictor and getattr(forecast_predictor, "_is_loaded", False)),
                "risk_predictor": bool(risk_predictor and getattr(risk_predictor, "_is_loaded", False)),
                "scenario_predictor": bool(scenario_predictor and getattr(scenario_predictor, "_is_loaded", False)),
                "r0_predictor": bool(loaded_predictors.get("r0") and getattr(loaded_predictors["r0"], "_is_loaded", False)),
            },
        },
        "outbreak_summary": {
            "total_confirmed_cases": totals.get("total_confirmed", 0),
            "total_deaths": totals.get("total_deaths", 0),
            "total_recovered": totals.get("total_recovered", 0),
            "total_active_cases": totals.get("total_active", 0),
            "total_bed_demand": totals.get("total_bed_demand", 0),
            "total_icu_demand": totals.get("total_icu_demand", 0),
            "total_ventilator_demand": totals.get("total_vent_demand", 0),
            "avg_reproduction_rate": totals.get("avg_r0", 0),
            "avg_case_fatality_rate": totals.get("avg_cfr", 0),
        },
        "current_capacity": {
            "bed_occupancy": round(cap["occupancy"], 1), "available_beds": cap["available"],
            "total_beds": cap["total"], "icu_capacity": cap["icu"], "hospitals": cap["hospitals"],
        },
        "ml_predicted_capacity": {
            "predicted_total_beds": ml_total, "predicted_icu_beds": ml_icu,
            "predicted_available_beds": ml_avail,
            "model": "GradientBoostingRegressor" if (bed_predictor and getattr(bed_predictor, "_is_loaded", False)) else "DB fallback",
            "ml_death_rate_per_100k": ml_death_rate,
            "ml_model": "GradientBoostingRegressor" if ml_death_rate else "DB fallback",
        },
        "projected_impact": {
            "bed_occupancy": projected_occupancy, "available_beds": max(0, ml_avail - peak_bed_demand),
            "bed_shortage": bed_shortage, "icu_shortage": icu_shortage,
            "projected_deaths": total_year_deaths, "projected_cfr": totals.get("avg_cfr", 0),
            "projected_bed_demand": peak_bed_demand, "projected_icu_demand": peak_icu_demand,
        },
        "tolerability": {
            "risk_score": risk_score, "risk_level": risk_level, "verdict": verdict,
            "bed_occupancy_risk": int(projected_occupancy),
            "fatality_risk": min(20, int(totals.get("avg_cfr", 0) / 2.5)),
            "icu_capacity_risk": min(10, int(max(0, peak_icu_demand - ml_icu) / max(peak_icu_demand, 1) * 10)),
            "bed_demand_risk": min(85, int((total_year_deaths ** 0.5) * 0.5)),
        },
        "monthly_breakdown": projected_monthly,
        "hospitals_at_risk": hospitals_at_risk,
        "recommendations": recommendations,
        "recommendations_detailed": [
            {"priority": i + 1, "message": rec, "category": "lockdown" if "lockdown" in rec.lower() else "capacity" if "bed" in rec.lower() or "icu" in rec.lower() else "containment" if "containment" in rec.lower() else "alert"}
            for i, rec in enumerate(recommendations)
        ],
        "lockdown_recommended": lockdown_info.get("lockdown_recommended", False),
        "yearly_r0_trend": yearly_r0_data,
    }
