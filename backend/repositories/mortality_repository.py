"""
WHAT THIS FILE DOES:
Handles all DATABASE QUERIES related to mortality (death) data. Retrieves
death counts by cause, district risk levels, and mortality trends. Used by
the Mortality Analytics page and the AI assistant to answer questions about
death rates and high-risk districts.

MortalityRepository - Concrete repository for mortality records
"""

import logging
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.core.base_repository import BaseRepository
from backend.models import MortalityRecord

logger = logging.getLogger(__name__)


class MortalityRepository(BaseRepository):
    """
    Concrete repository for MortalityRecord table.    """

    def __init__(self, db: Session):
        super().__init__(db, MortalityRecord)

    def get_by_state(self, state: str) -> list[MortalityRecord]:
        """Get all mortality records for a state."""
        return self._db.query(MortalityRecord).filter(
            MortalityRecord.state == state
        ).all()

    def get_by_district(self, district: str) -> list[MortalityRecord]:
        """Get mortality records for a specific district."""
        return self._db.query(MortalityRecord).filter(
            MortalityRecord.district == district
        ).all()

    def get_by_risk_level(self, risk_cluster: str) -> list[MortalityRecord]:
        """Get records by risk level."""
        return self._db.query(MortalityRecord).filter(
            MortalityRecord.risk_cluster == risk_cluster
        ).all()

    def get_summary_stats(self) -> dict[str, Any]:
        """Get aggregated mortality statistics."""
        result = self._db.query(
            func.avg(MortalityRecord.death_rate).label("avg_rate"),
            func.max(MortalityRecord.death_rate).label("max_rate"),
            func.min(MortalityRecord.death_rate).label("min_rate")
        ).first()
        return {
            "avg_death_rate": round(float(result.avg_rate or 0), 2) if result.avg_rate else 0.0,
            "max_death_rate": round(float(result.max_rate or 0), 2) if result.max_rate else 0.0,
            "min_death_rate": round(float(result.min_rate or 0), 2) if result.min_rate else 0.0,
            "unit": "per 100,000 population"
        }

    def get_top_risk_districts(self, limit: int = 10) -> list[dict]:
        """Get districts with highest death rates."""
        records = self._db.query(MortalityRecord).order_by(
            MortalityRecord.death_rate.desc()
        ).limit(limit).all()
        return [{
            "district": r.district,
            "state": r.state,
            "death_rate": r.death_rate,
            "risk_level": r.risk_cluster
        } for r in records]

    def get_by_cause(self, cause: str) -> list[MortalityRecord]:
        """Get records by cause of death."""
        return self._db.query(MortalityRecord).filter(
            MortalityRecord.cause_of_death == cause
        ).all()

    def get_by_age_group(self, age_group: str) -> list[MortalityRecord]:
        """Get records by age group (if available in schema)."""
        # This assumes age_group is a field in MortalityRecord
        if hasattr(MortalityRecord, 'age_group'):
            return self._db.query(MortalityRecord).filter(
                MortalityRecord.age_group == age_group
            ).all()
        return []
