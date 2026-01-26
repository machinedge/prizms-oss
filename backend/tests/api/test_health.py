"""Tests for health check endpoints."""

import pytest
from fastapi.testclient import TestClient

from api import app


client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_health_check(self):
        """Health endpoint should return 200 with status."""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["version"] == "0.1.0"

    def test_readiness_check(self):
        """Readiness endpoint should return 200 with component status."""
        response = client.get("/api/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "database" in data
        assert "providers" in data

    def test_health_response_structure(self):
        """Health response should have correct structure."""
        response = client.get("/api/health")
        data = response.json()
        assert set(data.keys()) == {"status", "version"}

    def test_readiness_response_structure(self):
        """Readiness response should have correct structure."""
        response = client.get("/api/ready")
        data = response.json()
        assert set(data.keys()) == {"status", "database", "providers"}
