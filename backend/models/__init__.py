"""
WHAT THIS FILE DOES:
Defines the DATABASE TABLES (schema) as Python classes. Each class = one table:
  - HospitalBed: bed availability data per hospital per month
  - MortalityRecord: death records by cause, age group, district
  - HospitalOutcome: hospital performance metrics (success rate, score)
  - PatientAdmission: patient admission records per hospital
  - ChatHistory: stores AI assistant conversations
  - User: user accounts for authentication

These are "models" that SQLAlchemy uses to convert between Python objects
and database rows automatically.

SQLAlchemy ORM Models for HospitalIQ
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Date, JSON, Text
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


class StateSummary(Base):
    """Pre-computed aggregation table for state-level stats.
    Populated at startup and refreshed every hour.
    Replaces all heavy live aggregation queries on /locations/stats.
    """
    __tablename__ = "state_summaries"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=True, index=True)   # NULL = All India row

    # Hospital stats
    distinct_hospitals   = Column(Integer, default=0)
    hosp_records         = Column(Integer, default=0)
    total_beds           = Column(Integer, default=0)
    avg_success_rate     = Column(Float, default=0)   # already ×100
    avg_score            = Column(Float, default=0)   # already ×100
    fatality_rate        = Column(Float, default=0)   # already ×100

    # Best hospital (JSON object)
    best_hospital        = Column(JSON, nullable=True)

    # Mortality stats
    mort_records         = Column(Integer, default=0)
    avg_death_rate       = Column(Float, default=0)
    total_deaths         = Column(Integer, default=0)
    total_population     = Column(Integer, default=0)
    common_causes        = Column(JSON, nullable=True)   # list of {cause, deaths}

    # Bed occupancy
    avg_occupancy        = Column(Float, default=0)

    updated_at = Column(DateTime, default=datetime.now(timezone.utc))


class DistrictSummary(Base):
    """Pre-computed aggregation table for district-level stats.
    Populated alongside state summaries.
    Replaces heavy district-level aggregation queries on the dashboard.
    """
    __tablename__ = "district_summaries"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)

    # Hospital stats
    hospitals            = Column(Integer, default=0)
    records              = Column(Integer, default=0)
    total_beds           = Column(Integer, default=0)
    avg_score            = Column(Float, default=0)
    success_rate         = Column(Float, default=0)
    fatality_rate        = Column(Float, default=0)

    # Mortality stats
    avg_death_rate       = Column(Float, default=0)
    total_deaths         = Column(Integer, default=0)
    population           = Column(Integer, default=0)

    updated_at = Column(DateTime, default=datetime.now(timezone.utc))


class HospitalBed(Base):
    """Hospital bed availability records"""
    __tablename__ = "hospital_beds"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True)
    hospital_name = Column(String(255), nullable=True)
    ward_type = Column(String(50), nullable=True)
    total_beds = Column(Integer, nullable=True)
    available_beds = Column(Integer, nullable=True)
    occupancy_rate = Column(Float, nullable=True)
    recorded_month = Column(Integer, nullable=True)
    recorded_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class MortalityRecord(Base):
    """Mortality and death rate records (monthly)"""
    __tablename__ = "mortality_records"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False, index=True)
    month = Column(Integer, nullable=True, default=6)
    age_group = Column(String(50), nullable=True)
    cause_of_death = Column(String(255), nullable=True)
    death_count = Column(Integer, nullable=True)
    death_rate = Column(Float, nullable=True)
    population = Column(Integer, nullable=True)
    risk_cluster = Column(String(50), index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class HospitalOutcome(Base):
    """Hospital performance and outcomes summary"""
    __tablename__ = "hospital_outcomes"

    id = Column(Integer, primary_key=True, index=True)
    hospital_id = Column(String(50), index=True)
    hospital_name = Column(String(255), nullable=False)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=True)
    hospital_type = Column(String(50), nullable=True)
    disease = Column(String(100), nullable=False, index=True)
    total_cases = Column(Integer, nullable=True)
    success_count = Column(Integer, nullable=True)
    failure_count = Column(Integer, nullable=True)
    success_rate = Column(Float, nullable=True)
    avg_stay_days = Column(Float, nullable=True)
    total_beds = Column(Integer, nullable=True)
    icu_beds = Column(Integer, nullable=True)
    specialist_count = Column(Integer, nullable=True)
    accreditation = Column(String(50), nullable=True)
    hospital_score = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class PatientAdmission(Base):
    """Patient-level admission records"""
    __tablename__ = "patient_admissions"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(50), nullable=True)
    admission_date = Column(Date, nullable=False, index=True)
    discharge_date = Column(Date, nullable=True)
    hospital_id = Column(String(50), nullable=True, index=True)
    hospital_name = Column(String(255), nullable=True)
    state = Column(String(100), nullable=True)
    disease = Column(String(100), nullable=True)
    age_group = Column(String(50), nullable=True)
    gender = Column(String(20), nullable=True)
    admission_type = Column(String(50), nullable=True)
    outcome = Column(String(50), nullable=True)
    stay_days = Column(Integer, nullable=True)
    treatment_cost = Column(Float, nullable=True)
    insurance_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class User(Base):
    """User accounts for authentication"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class ChatHistory(Base):
    """AI chat conversation history"""
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), nullable=False, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(String(5000), nullable=False)
    intent_detected = Column(String(50), nullable=True)
    context_used = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class PandemicOutbreak(Base):
    """Disease-specific outbreak records for pandemic scenario simulation"""
    __tablename__ = "pandemic_outbreak"

    id = Column(Integer, primary_key=True, index=True)
    disease = Column(String(100), nullable=False, index=True)
    state = Column(String(100), nullable=False, index=True)
    district = Column(String(100), nullable=False, index=True)
    year = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    confirmed_cases = Column(Integer, nullable=True, default=0)
    deaths = Column(Integer, nullable=True, default=0)
    recovered = Column(Integer, nullable=True, default=0)
    active_cases = Column(Integer, nullable=True, default=0)
    bed_demand = Column(Integer, nullable=True, default=0)
    icu_demand = Column(Integer, nullable=True, default=0)
    ventilator_demand = Column(Integer, nullable=True, default=0)
    reproduction_rate = Column(Float, nullable=True)
    case_fatality_rate = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class PredictionLog(Base):
    """Logs of all predictions made"""
    __tablename__ = "prediction_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    module = Column(String(50), nullable=True, index=True)
    input_params = Column(JSON, nullable=True)
    prediction_result = Column(JSON, nullable=True)
    model_version = Column(String(50), nullable=True)
    response_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), index=True)


class VirusRegistry(Base):
    """Pandemic virus metadata: fatality rate, reproduction rate, vaccine effectiveness"""
    __tablename__ = "virus_registry"

    id = Column(Integer, primary_key=True, index=True)
    virus_name = Column(String(100), unique=True, nullable=False, index=True)
    fatality_rate = Column(Float, nullable=True)
    reproductive_rate = Column(Float, nullable=True)
    incubation_period_days = Column(Integer, nullable=True)
    transmission_mode = Column(String(50), nullable=True)
    vaccine_available = Column(Boolean, default=False)
    vaccine_effectiveness = Column(Float, nullable=True)
    treatment_available = Column(Boolean, default=False)
    notes = Column(String(2000), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class Patient(Base):
    """Patient demographics and personal records"""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)
    age = Column(Integer, nullable=True)
    blood_group = Column(String(10), nullable=True)
    gender = Column(String(20), nullable=True)
    contact = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    state = Column(String(100), nullable=True, index=True)
    district = Column(String(100), nullable=True)
    pre_existing_conditions = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class VaccineHistory(Base):
    """Patient vaccination records"""
    __tablename__ = "vaccine_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, nullable=False, index=True)
    vaccine_name = Column(String(100), nullable=False)
    dose_number = Column(Integer, nullable=True)
    vaccination_date = Column(Date, nullable=True)
    hospital_name = Column(String(255), nullable=True)
    batch_number = Column(String(100), nullable=True)
    virus_name = Column(String(100), nullable=True)
    effectiveness = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class TravelHistory(Base):
    """Patient travel records for pandemic risk assessment"""
    __tablename__ = "travel_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, nullable=False, index=True)
    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    travel_date = Column(Date, nullable=True)
    return_date = Column(Date, nullable=True)
    purpose = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))


class FamilyHistory(Base):
    """Patient family medical history"""
    __tablename__ = "family_history"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, nullable=False, index=True)
    relationship = Column(String(50), nullable=True)
    condition = Column(String(255), nullable=True)
    age_at_diagnosis = Column(Integer, nullable=True)
    is_deceased = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
