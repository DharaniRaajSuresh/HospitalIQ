"""
backend/repositories/__init__.py - Export concrete repositories
"""

from backend.repositories.bed_repository import BedRepository
from backend.repositories.mortality_repository import MortalityRepository
from backend.repositories.hospital_repository import HospitalRepository
from backend.repositories.user_repository import UserRepository

__all__ = [
    "BedRepository",
    "MortalityRepository",
    "HospitalRepository",
    "UserRepository",
]
