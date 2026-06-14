from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models import Patient, VaccineHistory, TravelHistory, FamilyHistory, VirusRegistry
import logging

logger = logging.getLogger(__name__)


class PatientRepository:
    def __init__(self, db: Session):
        self._db = db

    def get_all(self, skip: int = 0, limit: int = 100, state: str = None, search: str = None) -> List[Patient]:
        q = self._db.query(Patient)
        if state:
            q = q.filter(Patient.state == state)
        if search:
            q = q.filter(Patient.patient_name.ilike(f"%{search}%"))
        return q.order_by(Patient.id.desc()).offset(skip).limit(limit).all()

    def get_by_id(self, patient_id: int) -> Optional[Patient]:
        return self._db.query(Patient).filter(Patient.id == patient_id).first()

    def get_vaccine_history(self, patient_id: int) -> List[VaccineHistory]:
        return self._db.query(VaccineHistory).filter(VaccineHistory.patient_id == patient_id).order_by(VaccineHistory.vaccination_date.desc()).all()

    def get_travel_history(self, patient_id: int) -> List[TravelHistory]:
        return self._db.query(TravelHistory).filter(TravelHistory.patient_id == patient_id).order_by(TravelHistory.travel_date.desc()).all()

    def get_family_history(self, patient_id: int) -> List[FamilyHistory]:
        return self._db.query(FamilyHistory).filter(FamilyHistory.patient_id == patient_id).all()

    def get_summary_stats(self) -> Dict[str, Any]:
        result = self._db.query(func.count(Patient.id), func.avg(Patient.age)).first()
        return {
            "total_patients": result[0] or 0,
            "avg_age": round(float(result[1]), 1) if result[1] else 0,
        }

    def get_viruses(self) -> List[VirusRegistry]:
        return self._db.query(VirusRegistry).order_by(VirusRegistry.virus_name).all()

    def get_virus_by_name(self, name: str) -> Optional[VirusRegistry]:
        return self._db.query(VirusRegistry).filter(VirusRegistry.virus_name == name).first()
