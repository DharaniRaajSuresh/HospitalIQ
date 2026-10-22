"""
backend/processors/__init__.py - Export concrete processors
"""

from backend.processors.bed_processor import BedDataProcessor
from backend.processors.hospital_processor import HospitalDataProcessor
from backend.processors.mortality_processor import MortalityDataProcessor

__all__ = [
    "BedDataProcessor",
    "MortalityDataProcessor",
    "HospitalDataProcessor",
]
