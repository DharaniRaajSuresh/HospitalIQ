"""
Integration tests for FastAPI endpoints with in-memory SQLite DB.
Tests all registered API routes from main.py.
"""
import os

os.environ["SKIP_DB_INIT"] = "1"


class TestHealth:
    def test_health_check(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "database" in data
        assert "models_loaded" in data

    def test_root(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "application" in data


class TestBeds:
    def test_predict_beds(self, client, auth_headers, seed_beds):
        resp = client.post("/api/v1/predict/beds", params={
            "state": "Tamil Nadu", "ward_type": "ICU", "months_ahead": 3
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "state" in data
        assert data["state"] == "Tamil Nadu"

    def test_predict_beds_invalid_state(self, client, auth_headers):
        resp = client.post("/api/v1/predict/beds", params={
            "state": "Atlantis", "ward_type": "ICU", "months_ahead": 3
        }, headers=auth_headers)
        assert resp.status_code in [404, 503]

    def test_predict_beds_with_data(self, client, seed_beds, auth_headers):
        resp = client.post("/api/v1/predict/beds", params={
            "state": "Tamil Nadu", "ward_type": "General", "months_ahead": 6
        }, headers=auth_headers)
        assert resp.status_code == 200


class TestMortality:
    def test_predict_mortality(self, client, auth_headers, seed_mortality):
        resp = client.post("/api/v1/predict/mortality", params={
            "district": "Chennai", "age_group": "45-64",
            "cause": "Cardiac", "year": 2024, "month": 6,
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "district" in data

    def test_predict_mortality_bad_age(self, client, auth_headers):
        resp = client.post("/api/v1/predict/mortality", params={
            "district": "Chennai", "age_group": "999+",
            "cause": "Cardiac", "year": 2024, "month": 6,
        }, headers=auth_headers)
        assert resp.status_code in [200, 404]
        data = resp.json()
        assert isinstance(data, dict)

    def test_predict_mortality_with_data(self, client, seed_mortality, auth_headers):
        resp = client.post("/api/v1/predict/mortality", params={
            "district": "Chennai", "age_group": "45-64",
            "cause": "Cardiac", "year": 2024, "month": 6,
        }, headers=auth_headers)
        assert resp.status_code == 200


class TestPandemic:
    def test_pandemic_scenario(self, client, seed_pandemic, auth_headers):
        resp = client.get("/api/v1/pandemic/scenario", params={
            "disease": "COVID-19", "state": "Kerala",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    def test_pandemic_scenario_unknown_disease(self, client, auth_headers):
        resp = client.get("/api/v1/pandemic/scenario", params={
            "disease": "AlienFlu", "state": "Kerala",
        }, headers=auth_headers)
        assert resp.status_code in [200, 404]


class TestLocations:
    def test_get_states(self, client):
        resp = client.get("/api/v1/states")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_get_districts(self, client):
        resp = client.get("/api/v1/districts?state=Tamil+Nadu")
        assert resp.status_code == 200

    def test_locations_stats(self, client):
        resp = client.get("/api/v1/locations/stats")
        assert resp.status_code == 200

    def test_district_list(self, client):
        resp = client.get("/api/v1/locations/district-list?state=Tamil+Nadu")
        assert resp.status_code == 200

    def test_localities(self, client):
        resp = client.get("/api/v1/locations/localities?district=Chennai")
        assert resp.status_code == 200

    def test_hospital_rankings(self, client):
        resp = client.get("/api/v1/hospitals/rankings", params={"disease": "Cardiac"})
        assert resp.status_code == 200


class TestAI:
    def test_ai_chat(self, client, auth_headers):
        resp = client.post("/api/v1/ai/chat", json={"message": "Hello", "session_id": "test-123"}, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data or "response" in data or "message" in data

    def test_ai_suggestions_get(self, client, auth_headers):
        resp = client.get("/api/v1/ai/suggestions?query=beds", headers=auth_headers)
        assert resp.status_code == 200


class TestStats:
    def test_stats_endpoint(self, client, auth_headers):
        resp = client.get("/api/v1/stats", headers=auth_headers)
        assert resp.status_code == 200


class TestMap:
    def test_geojson(self, client, auth_headers):
        resp = client.get("/api/v1/map/geojson", headers=auth_headers)
        assert resp.status_code == 200


class TestAudit:
    def test_health_audit(self, client, auth_headers):
        resp = client.get("/api/v1/health/audit", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["audit_version"] == "1.0"
        assert "models_total" in data
        assert "data_provenance" in data
        assert "deployment_readiness" in data
        assert "models_detail" in data
