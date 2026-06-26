"""
WHAT THIS FILE DOES:
Defines the BLUEPRINT for all database access classes (Abstraction).
Provides shared CRUD operations (count(), get_all(), get_by_id()) that
all repositories inherit. Specific repositories (Bed, Hospital, Mortality)
add their own query methods on top.

This implements the "Repository Pattern" — instead of writing SQL everywhere,
each table has a dedicated class that owns all its queries.

BaseRepository - Abstract Base Class for all database access
Demonstrates: Abstraction, Encapsulation, Inheritance
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(ABC):
    """
    Abstract base class for all database access.
    
    OOP Principles:
    - Abstraction: defines interface via abstract methods
    - Encapsulation: DB session kept private (_db)
    - Inheritance: all repositories extend this class
    - Polymorphism: get_by_state() and get_summary_stats() vary by subclass
    """

    def __init__(self, db: Session, model_class: type[T]):
        self._db = db                              # Encapsulated
        self._model_class = model_class            # Encapsulated

    # Concrete shared CRUD methods (Inheritance benefit)
    def get_by_id(self, record_id: int) -> T | None:
        """Get single record by ID."""
        return self._db.query(self._model_class).filter(
            self._model_class.id == record_id
        ).first()

    def get_all(self, skip: int = 0, limit: int = 100) -> list[T]:
        """Get all records with pagination."""
        return self._db.query(self._model_class).offset(skip).limit(limit).all()

    def count(self) -> int:
        """Count total records in table."""
        return self._db.query(self._model_class).count()

    def create(self, obj_data: dict[str, Any]) -> T:
        """Create single record."""
        db_obj = self._model_class(**obj_data)
        self._db.add(db_obj)
        self._db.commit()
        self._db.refresh(db_obj)
        return db_obj

    def bulk_insert(self, records: list[dict[str, Any]]) -> int:
        """Insert multiple records efficiently."""
        self._db.bulk_insert_mappings(self._model_class, records)
        self._db.commit()
        return len(records)

    def delete(self, record_id: int) -> bool:
        """Delete record by ID."""
        obj = self.get_by_id(record_id)
        if obj:
            self._db.delete(obj)
            self._db.commit()
            return True
        return False

    def get_latest(self, limit: int = 10) -> list[T]:
        """Get most recently created records."""
        return self._db.query(self._model_class).order_by(
            self._model_class.id.desc()
        ).limit(limit).all()

    # Abstract: each repository adds domain-specific queries
    @abstractmethod
    def get_by_state(self, state: str) -> list[T]:
        """Filter by state. Implementation varies by domain."""
        pass

    @abstractmethod
    def get_summary_stats(self) -> dict[str, Any]:
        """Get aggregated statistics. Implementation varies by domain."""
        pass
