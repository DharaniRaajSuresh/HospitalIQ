import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth import require_user
from backend.database import get_db
from backend.models import HospitalOutcome, Patient, User

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
def global_search(q: str = Query("", min_length=1, max_length=200),
                  limit: int = Query(8, ge=1, le=50),
                  db: Session = Depends(get_db),
                  _: User = Depends(require_user)):
    term = f"%{q}%"

    patients = (
        db.query(Patient.id, Patient.patient_name, Patient.state, Patient.district)
        .filter(Patient.patient_name.ilike(term))
        .limit(limit)
        .all()
    )

    hospitals = (
        db.query(
            HospitalOutcome.hospital_id,
            HospitalOutcome.hospital_name,
            HospitalOutcome.state,
            HospitalOutcome.district,
            HospitalOutcome.hospital_type,
        )
        .filter(HospitalOutcome.hospital_name.ilike(term))
        .distinct(HospitalOutcome.hospital_name)
        .limit(limit)
        .all()
    )

    return {
        "patients": [
            {"id": p.id, "name": p.patient_name, "state": p.state, "district": p.district}
            for p in patients
        ],
        "hospitals": [
            {"id": h.hospital_id, "name": h.hospital_name, "state": h.state,
             "district": h.district, "type": h.hospital_type}
            for h in hospitals
        ],
        "query": q,
    }
