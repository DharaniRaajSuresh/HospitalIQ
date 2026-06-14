"""
pytest fixtures: in-memory SQLite DB, test data, overridden dependencies
"""
import os

import pytest

os.environ["SKIP_DB_INIT"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///./test_hospitaliq.db"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.auth import get_password_hash
from backend.database import Base, get_db
from backend.main import app
from backend.models import (
    HospitalBed,
    HospitalOutcome,
    MortalityRecord,
    PandemicOutbreak,
    User,
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_engine("sqlite:///./test_hospitaliq.db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(test_engine):
    TestSession = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)
    session = TestSession()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def auth_headers(client, db_session):
    existing = db_session.query(User).filter(User.email == "test@hospitaliq.io").first()
    if not existing:
        user = User(email="test@hospitaliq.io", hashed_password=get_password_hash("testpass"), full_name="Tester")
        db_session.add(user)
        db_session.commit()
    resp = client.post("/api/v1/auth/login", json={"email": "test@hospitaliq.io", "password": "testpass"})
    token = resp.json().get("access_token", "")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def seed_beds(db_session):
    states = ["Tamil Nadu", "Kerala", "Delhi"]
    wards = ["ICU", "General", "Emergency"]
    for state in states:
        for ward in wards:
            for m in range(1, 13):
                bed = HospitalBed(
                    state=state, district="Chennai", hospital_name=f"{state} General",
                    ward_type=ward, total_beds=200, available_beds=150,
                    occupancy_rate=25.0, recorded_month=m % 12 + 1,
                    recorded_year=2024,
                )
                db_session.add(bed)
    db_session.commit()


@pytest.fixture(scope="function")
def seed_pandemic(db_session):
    diseases = ["COVID-19", "Ebola", "H1N1"]
    states = ["Maharashtra", "Kerala"]
    for disease in diseases:
        for state in states:
            for m in range(1, 7):
                p = PandemicOutbreak(
                    disease=disease, state=state, district="Test",
                    year=2024, month=m,
                    confirmed_cases=1000 * m,
                    deaths=int(1000 * m * 0.02),
                    recovered=int(1000 * m * 0.9),
                    active_cases=int(1000 * m * 0.08),
                    case_fatality_rate=2.0,
                    reproduction_rate=1.5,
                    bed_demand=int(1000 * m * 0.15),
                    icu_demand=int(1000 * m * 0.05),
                )
                db_session.add(p)
    db_session.commit()


@pytest.fixture(scope="function")
def seed_mortality(db_session):
    for state, district in [("Tamil Nadu", "Chennai"), ("Kerala", "Thiruvananthapuram")]:
        for cause in ["Cardiac", "Respiratory"]:
            for age in ["0-14", "45-64"]:
                for m in range(1, 7):
                    mr = MortalityRecord(
                        state=state, district=district,
                        age_group=age, cause_of_death=cause,
                        year=2024, month=m,
                        death_rate=50.0 + m * 5,
                        population=1000000,
                        death_count=int((50.0 + m * 5) * 10),
                    )
                    db_session.add(mr)
    db_session.commit()


@pytest.fixture(scope="function")
def seed_hospitals(db_session):
    for state in ["Tamil Nadu", "Kerala"]:
        for disease in ["Cardiac", "Diabetes"]:
            ho = HospitalOutcome(
                hospital_name=f"{state} Hospital",
                state=state, district="Chennai",
                hospital_type="Private",
                disease=disease,
                total_beds=200, icu_beds=30,
                avg_stay_days=5, specialist_count=15,
                accreditation="NABH",
                success_rate=0.85,
                hospital_score=85.0,
                rating=4.2,
            )
            db_session.add(ho)
    db_session.commit()
