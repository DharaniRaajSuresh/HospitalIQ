"""
backend/processors/__init__.py - Export concrete processors
"""

from backend.processors.bed_processor import BedDataProcessor
from backend.processors.mortality_processor import MortalityDataProcessor
from backend.processors.hospital_processor import HospitalDataProcessor

__all__ = [
    "BedDataProcessor",
    "MortalityDataProcessor",
    "HospitalDataProcessor",
]
