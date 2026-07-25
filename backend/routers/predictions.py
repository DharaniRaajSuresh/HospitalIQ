"""Prediction endpoints: beds, mortality"""
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func

from backend.app_state import loaded_predictors, normalize_state
from backend.auth import require_user
from backend.database import get_db
from backend.models import HospitalBed, MortalityRecord, PredictionLog
from backend.predictors.risk_utils import assign_risk_level

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Predictions"], prefix="/api/v1/predict")


def _log_pred(db, module, params, source):
    try:
        db.add(PredictionLog(module=module, input_params=params, prediction_result={"source": source},
                             model_version=f"{module}_v1", response_time_ms=0, created_at=datetime.now(UTC)))
        db.commit()
    except Exception as e:
        logger.warning("Prediction log failed: %s", e)
        db.rollback()


@router.post("/beds")
async def predict_beds(state: str, ward_type: str, months_ahead: int = 3, year: int = Query(None), db=Depends(get_db), user=Depends(require_user)):
    state = normalize_state(state)
    start_year = year if year else datetime.now().year
    start_month = 1 if year else datetime.now().month

    db_data = db.query(
        HospitalBed.recorded_month, HospitalBed.recorded_year,
        func.avg(HospitalBed.available_beds), func.avg(HospitalBed.total_beds),
        func.avg(HospitalBed.occupancy_rate)
    ).filter(HospitalBed.state == state, HospitalBed.ward_type == ward_type
    ).group_by(HospitalBed.recorded_year, HospitalBed.recorded_month
    ).order_by(HospitalBed.recorded_year, HospitalBed.recorded_month).all()

    try:
        if "bed" in loaded_predictors:
            predictor = loaded_predictors["bed"]
            result = predictor.predict({"state": state, "ward_type": ward_type,
                                        "months_ahead": months_ahead,
                                        "start_year": start_year, "start_month": start_month})
            resp = {"state": state, "ward_type": ward_type, "forecast": result if isinstance(result, list) else [result], "status": "ml_model"}
            _log_pred(db, "beds", {"state": state, "ward_type": ward_type, "months_ahead": months_ahead, "year": start_year}, "ml_model")
            return resp
    except Exception as e:
        logger.error(f"Bed prediction error: {e}")

    if db_data:
        if db_data[-1][2] is None or db_data[-1][3] is None:
            raise HTTPException(status_code=404, detail="Incomplete historical data for this state/ward")
        base_available = db_data[-1][2]
        base_total = db_data[-1][3]
        trend = 0
        if len(db_data) >= 3:
            if any(r[2] is None for r in db_data[-3:]):
                raise HTTPException(status_code=404, detail="Incomplete historical data for trend calculation")
            recent = [r[2] for r in db_data[-3:]]
            trend = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
        month_map = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        forecasts = []
        for i in range(months_ahead):
            predicted = max(0, round(base_available + trend * (i + 1)))
            month_idx = ((start_month - 1 + i) % 12) + 1
            year_val = start_year + (start_month - 1 + i) // 12
            forecasts.append({"month": month_map[month_idx], "year": year_val,
                              "predicted_beds": predicted, "available_beds": predicted,
                              "occupancy_rate": round(max(0, 1 - predicted / max(base_total, 1)), 2)})
        resp = {"state": state, "ward_type": ward_type, "forecast": forecasts, "status": "db_trend"}
        _log_pred(db, "beds", {"state": state, "ward_type": ward_type, "months_ahead": months_ahead, "year": start_year}, "db_trend")
        return resp
    raise HTTPException(status_code=404, detail="Bed predictor unavailable and no historical data for this state/ward")


@router.post("/mortality")
async def predict_mortality(district: str, age_group: str, cause: str, year: int = 2024, month: int = 6, db=Depends(get_db), _=Depends(require_user)):
    try:
        if "mortality" in loaded_predictors:
            predictor = loaded_predictors["mortality"]
            result = predictor.predict({"district": district, "age_group": age_group, "cause": cause, "year": year, "month": month})
            resp = {"district": district, "age_group": age_group, "cause": cause, "result": result, "status": "ml_model"}
            _log_pred(db, "mortality", {"district": district, "age_group": age_group, "cause": cause}, "ml_model")
            return resp
    except Exception as e:
        logger.error(f"Mortality model error: {e}")

    db_avg = db.query(func.avg(MortalityRecord.death_rate)).filter(
        MortalityRecord.district == district, MortalityRecord.age_group == age_group,
        MortalityRecord.cause_of_death == cause).scalar()
    if db_avg is None:
        raise HTTPException(status_code=404, detail="Mortality predictor unavailable and no historical data for this district/age/cause")
    death_rate = float(db_avg)
    risk = assign_risk_level(death_rate)
    MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    resp = {"district": district, "age_group": age_group, "cause": cause,
            "result": {"district": district, "age_group": age_group, "cause": cause, "year": year, "month": month,
                       "month_name": MONTHS[month] if 0 < month < 13 else "Jun",
                       "predicted_death_rate": round(death_rate, 2), "risk_level": risk, "unit": "per 100,000 population"},
            "status": "db_grounded"}
    _log_pred(db, "mortality", {"district": district, "age_group": age_group, "cause": cause}, "db_grounded")
    return resp
