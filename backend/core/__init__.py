"""
backend/core/__init__.py - Export abstract base classes
"""

from backend.core.base_predictor import BasePredictor
from backend.core.base_repository import BaseRepository
from backend.core.base_processor import BaseDataProcessor

__all__ = [
    "BasePredictor",
    "BaseRepository",
    "BaseDataProcessor",
]
