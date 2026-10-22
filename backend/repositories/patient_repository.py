import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import FamilyHistory, Patient, TravelHistory, VaccineHistory, VirusRegistry

logger = logging.getLogger(__name__)


class PatientRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self, skip: int = 0, limit: int = 100, state: str = None, search: str = None) -> list[Patient]:
        q = self._db.query(Patient)
        if state:
            q = q.filter(Patient.state == state)
        if search:
            term = f"%{search}%"
            q = q.filter(
                Patient.patient_name.ilike(term)
                | Patient.state.ilike(term)
                | Patient.district.ilike(term)
                | Patient.blood_group.ilike(term)
                | Patient.gender.ilike(term)
            )
        return q.order_by(Patient.id.desc()).offset(skip).limit(limit).all()

    def get_by_id(self, patient_id: int) -> Patient | None:
        return self._db.query(Patient).filter(Patient.id == patient_id).first()

    def get_vaccine_history(self, patient_id: int) -> list[VaccineHistory]:
        return self._db.query(VaccineHistory).filter(VaccineHistory.patient_id == patient_id).order_by(VaccineHistory.vaccination_date.desc()).all()

    def get_travel_history(self, patient_id: int) -> list[TravelHistory]:
        return self._db.query(TravelHistory).filter(TravelHistory.patient_id == patient_id).order_by(TravelHistory.travel_date.desc()).all()

    def get_family_history(self, patient_id: int) -> list[FamilyHistory]:
        return self._db.query(FamilyHistory).filter(FamilyHistory.patient_id == patient_id).all()

    def get_summary_stats(self) -> dict[str, Any]:
        result = self._db.query(func.count(Patient.id), func.avg(Patient.age)).first()
        return {
            "total_patients": result[0] or 0,
            "avg_age": round(float(result[1]), 1) if result[1] else 0,
        }

    def get_viruses(self) -> list[VirusRegistry]:
        return self._db.query(VirusRegistry).order_by(VirusRegistry.virus_name).all()

    def get_virus_by_name(self, name: str) -> VirusRegistry | None:
        return self._db.query(VirusRegistry).filter(VirusRegistry.virus_name == name).first()
