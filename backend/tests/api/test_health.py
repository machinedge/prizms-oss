import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


class TestHealthEndpoints:

    def test_health_check(self):
        """Health endpoint should return 200 with status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data

    def test_readiness_check(self):
        """Readiness endpoint should return 200 with component status."""
        response = client.get("/api/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "database" in data
        assert "providers" in data
