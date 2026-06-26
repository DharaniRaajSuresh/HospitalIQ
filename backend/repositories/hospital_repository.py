"""
WHAT THIS FILE DOES:
Handles all DATABASE QUERIES related to hospital performance data
( success rates, scores, accreditations, patient counts). Used by both
the Hospital Rankings page and the AI assistant to fetch real hospital data.

Key methods: get_top_hospitals() for disease-specific rankings,
get_by_state() for location filtering, get_summary_stats() for aggregates.

HospitalRepository - Concrete repository for hospital outcomes
Demonstrates: Inheritance, Polymorphism
"""

import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.base_repository import BaseRepository
from backend.models import HospitalOutcome

logger = logging.getLogger(__name__)


class HospitalRepository(BaseRepository):
    """
    Concrete repository for HospitalOutcome table.
    
    OOP Principles:
    - Inheritance: extends BaseRepository
    - Polymorphism: hospital-specific queries
    """

    def __init__(self, db: Session):
        super().__init__(db, HospitalOutcome)

    def get_by_state(self, state: str) -> list[HospitalOutcome]:
        """Get all hospitals in a state."""
        return self._db.query(HospitalOutcome).filter(
            HospitalOutcome.state == state
        ).all()

    def get_by_disease(self, disease: str) -> list[HospitalOutcome]:
        """Get hospitals treating a specific disease."""
        return self._db.query(HospitalOutcome).filter(
            HospitalOutcome.disease == disease
        ).all()

    def get_by_disease_and_state(self, disease: str, state: str) -> list[HospitalOutcome]:
        """Get hospitals by disease and state."""
        return self._db.query(HospitalOutcome).filter(
            HospitalOutcome.disease == disease,
            HospitalOutcome.state == state
        ).all()

    def get_top_hospitals(self, disease: str, top_n: int = 10, state: str = None) -> list[dict]:
        """Get top performing hospitals for a disease."""
        q = self._db.query(HospitalOutcome).filter(
            HospitalOutcome.disease == disease
        )
        if state:
            q = q.filter(HospitalOutcome.state == state)

        results = q.order_by(HospitalOutcome.hospital_score.desc()).limit(top_n).all()
        return [{
            "rank": i + 1,
            "hospital_name": r.hospital_name,
            "district": r.district,
            "state": r.state,
            "disease": r.disease,
            "hospital_type": r.hospital_type,
            "success_rate": r.success_rate,
            "avg_stay_days": r.avg_stay_days,
            "hospital_score": r.hospital_score,
            "rating": r.rating,
            "accreditation": r.accreditation
        } for i, r in enumerate(results)]

    def get_summary_stats(self, state: str = None, disease: str = None) -> dict[str, Any]:
        """Get aggregated hospital statistics, optionally filtered by state and/or disease."""
        q = self._db.query(
            func.avg(HospitalOutcome.success_rate).label("avg_success"),
            func.avg(HospitalOutcome.rating).label("avg_rating"),
            func.count(func.distinct(HospitalOutcome.hospital_id)).label("unique_hospitals")
        )
        if state:
            q = q.filter(HospitalOutcome.state == state)
        if disease:
            q = q.filter(HospitalOutcome.disease == disease)
        result = q.first()
        return {
            "avg_success_rate": round(float(result.avg_success or 0), 2) if result.avg_success else 0.0,
            "avg_rating": round(float(result.avg_rating or 0), 2) if result.avg_rating else 0.0,
            "unique_hospitals": int(result.unique_hospitals or 0) if result.unique_hospitals else 0
        }

    def get_by_type(self, hospital_type: str) -> list[HospitalOutcome]:
        """Get hospitals by type (Govt, Private, Trust, etc)."""
        return self._db.query(HospitalOutcome).filter(
            HospitalOutcome.hospital_type == hospital_type
        ).all()

    def get_with_accreditation(self, accreditation: str) -> list[HospitalOutcome]:
        """Get hospitals with specific accreditation."""
        return self._db.query(HospitalOutcome).filter(
            HospitalOutcome.accreditation == accreditation
        ).all()
