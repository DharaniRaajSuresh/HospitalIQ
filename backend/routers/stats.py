"""Stats endpoint"""
import logging
import time
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import func

from backend.auth import get_current_user
from backend.database import get_db
from backend.models import HospitalBed, HospitalOutcome, MortalityRecord, PatientAdmission, User

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Analytics"], prefix="/api/v1")

_stats_cache = {"value": None, "ts": 0}
_STATS_TTL = 300  # 5 minutes


@router.get("/stats")
async def get_stats(db=Depends(get_db), _: Optional[User] = Depends(get_current_user)):
    if _stats_cache["value"] and (time.time() - _stats_cache["ts"]) < _STATS_TTL:
        return _stats_cache["value"]
    result = {
        "beds": db.query(func.count(HospitalBed.id)).scalar() or 0,
        "mortality_records": db.query(func.count(MortalityRecord.id)).scalar() or 0,
        "hospitals": db.query(func.count(HospitalOutcome.id)).scalar() or 0,
        "patients": db.query(func.count(PatientAdmission.id)).scalar() or 0,
        "districts": db.query(MortalityRecord.district).distinct().count(),
        "states": db.query(MortalityRecord.state).distinct().count(),
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _stats_cache["value"] = result
    _stats_cache["ts"] = time.time()
    return result
