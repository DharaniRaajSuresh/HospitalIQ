"""Tests for patient endpoints: list, detail, risk prediction, error handling."""
import os

os.environ["SKIP_DB_INIT"] = "1"

from backend.models import Patient, VirusRegistry


class TestListPatients:
    def _clean(self, db_session):
        db_session.query(Patient).delete()
        db_session.commit()

    def test_list_patients_returns_200_with_pagination(self, client, db_session, auth_headers):
        self._clean(db_session)
        db_session.add(Patient(patient_name="Test Patient", age=35, state="Tamil Nadu"))
        db_session.commit()

        resp = client.get("/api/v1/patients/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "patients" in data
        assert "total" in data
        assert data["total"] >= 1
        assert "skip" in data
        assert "limit" in data

    def test_list_patients_requires_auth(self, client):
        resp = client.get("/api/v1/patients/")
        assert resp.status_code == 401

    def test_list_patients_with_state_filter(self, client, db_session, auth_headers):
        self._clean(db_session)
        db_session.add(Patient(patient_name="Patient TN", state="Tamil Nadu"))
        db_session.add(Patient(patient_name="Patient KL", state="Kerala"))
        db_session.commit()

        resp = client.get("/api/v1/patients/?state=Tamil+Nadu", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        for p in data["patients"]:
            assert p["state"] == "Tamil Nadu"


class TestGetPatient:
    def _clean(self, db_session):
        db_session.query(Patient).delete()
        db_session.commit()

    def test_get_patient_returns_200(self, client, db_session, auth_headers):
        self._clean(db_session)
        db_session.add(Patient(patient_name="Alice", age=30, state="Kerala",
                               blood_group="O+", gender="Female"))
        db_session.commit()
        pid = db_session.query(Patient).filter(Patient.patient_name == "Alice").first().id

        resp = client.get(f"/api/v1/patients/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["patient"]["patient_name"] == "Alice"

    def test_get_patient_returns_404_for_missing(self, client, auth_headers):
        resp = client.get("/api/v1/patients/99999", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Patient not found"

    def test_get_patient_requires_auth(self, client):
        resp = client.get("/api/v1/patients/1")
        assert resp.status_code == 401

    def test_get_patient_invalid_id_returns_422(self, client, auth_headers):
        resp = client.get("/api/v1/patients/abc", headers=auth_headers)
        assert resp.status_code == 422

    def test_get_patient_negative_id_returns_404(self, client, auth_headers):
        resp = client.get("/api/v1/patients/-1", headers=auth_headers)
        assert resp.status_code == 404


class TestPatientRisk:
    def test_risk_endpoint_returns_404_for_missing_patient(self, client, db_session, auth_headers):
        db_session.query(VirusRegistry).delete()
        db_session.commit()
        db_session.add(VirusRegistry(virus_name="COVID-19", fatality_rate=0.02,
                                      reproductive_rate=2.5, vaccine_available=True,
                                      vaccine_effectiveness=0.9))
        db_session.commit()

        resp = client.get("/api/v1/patients/99999/risk?virus_name=COVID-19", headers=auth_headers)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Patient not found"

    def test_risk_endpoint_requires_auth(self, client):
        resp = client.get("/api/v1/patients/1/risk?virus_name=COVID-19")
        assert resp.status_code == 401

    def test_risk_endpoint_missing_virus_param(self, client, auth_headers):
        resp = client.get("/api/v1/patients/1/risk", headers=auth_headers)
        assert resp.status_code == 422
