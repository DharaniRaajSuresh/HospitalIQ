"""
WHAT THIS FILE DOES:
Handles all DATABASE QUERIES related to hospital bed data. Translates
Python method calls (like get_summary_stats() or get_by_state()) into
SQL queries against the hospital_beds table. Returns data as Python
dictionaries that the API endpoints can send to the frontend.

This is the "middleman" between the raw database and the prediction code.

BedRepository - Concrete repository for hospital beds
"""

import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.base_repository import BaseRepository
from backend.models import HospitalBed

logger = logging.getLogger(__name__)


class BedRepository(BaseRepository):
    """
    Concrete repository for HospitalBed table.    """

    def __init__(self, db: Session):
        super().__init__(db, HospitalBed)

    def get_by_state(self, state: str) -> list[HospitalBed]:
        """Get all bed records for a specific state."""
        return self._db.query(HospitalBed).filter(
            HospitalBed.state == state
        ).all()

    def get_by_state_and_ward(self, state: str, ward_type: str) -> list[HospitalBed]:
        """Get bed records filtered by state and ward type."""
        return self._db.query(HospitalBed).filter(
            HospitalBed.state == state,
            HospitalBed.ward_type == ward_type
        ).all()

    def get_summary_stats(self) -> dict[str, Any]:
        """Get aggregated bed statistics."""
        result = self._db.query(
            func.sum(HospitalBed.total_beds).label("total"),
            func.sum(HospitalBed.available_beds).label("available"),
            func.avg(HospitalBed.occupancy_rate).label("avg_occupancy")
        ).first()
        return {
            "total_beds": int(result.total or 0) if result.total else 0,
            "available_beds": int(result.available or 0) if result.available else 0,
            "avg_occupancy_rate": round(float(result.avg_occupancy or 0), 2) if result.avg_occupancy else 0.0
        }

    def get_monthly_trend(self, state: str, ward_type: str, year: int) -> list[dict]:
        """Get bed trend data for a state/ward/year."""
        records = self._db.query(HospitalBed).filter(
            HospitalBed.state == state,
            HospitalBed.ward_type == ward_type,
            HospitalBed.recorded_year == year
        ).order_by(HospitalBed.recorded_month).all()
        return [{
            "month": r.recorded_month,
            "available": r.available_beds,
            "total": r.total_beds,
            "occupancy": r.occupancy_rate
        } for r in records]

    def get_by_state_and_month(self, state: str, month: int, year: int) -> list[HospitalBed]:
        """Get records for specific month and year."""
        return self._db.query(HospitalBed).filter(
            HospitalBed.state == state,
            HospitalBed.recorded_month == month,
            HospitalBed.recorded_year == year
        ).all()
