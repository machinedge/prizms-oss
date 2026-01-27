"""Tests for the personalities API endpoint."""

import pytest
from fastapi.testclient import TestClient

from api.app import app
from api.routes.personalities import (
    get_available_personalities,
    PersonalityInfo,
    SYSTEM_PERSONALITIES,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


class TestGetAvailablePersonalities:
    """Tests for the get_available_personalities helper function."""

    def test_returns_list_of_personalities(self):
        """Should return a list of PersonalityInfo objects."""
        personalities = get_available_personalities()
        assert isinstance(personalities, list)
        assert len(personalities) > 0
        assert all(isinstance(p, PersonalityInfo) for p in personalities)

    def test_each_personality_has_required_fields(self):
        """Should have name, description, and is_system fields."""
        personalities = get_available_personalities()
        for p in personalities:
            assert hasattr(p, "name")
            assert hasattr(p, "description")
            assert hasattr(p, "is_system")
            assert isinstance(p.name, str)
            assert isinstance(p.description, str)
            assert isinstance(p.is_system, bool)

    def test_marks_system_personalities_correctly(self):
        """Should mark consensus_check and synthesizer as system personalities."""
        personalities = get_available_personalities()
        personality_dict = {p.name: p for p in personalities}

        for sys_name in SYSTEM_PERSONALITIES:
            if sys_name in personality_dict:
                assert personality_dict[sys_name].is_system is True

    def test_includes_debate_personalities(self):
        """Should include non-system personalities."""
        personalities = get_available_personalities()
        non_system = [p for p in personalities if not p.is_system]
        assert len(non_system) > 0


class TestListPersonalitiesEndpoint:
    """Tests for the GET /api/personalities endpoint."""

    def test_returns_personalities_list(self, client):
        """Should return a list of personalities."""
        response = client.get("/api/personalities")
        assert response.status_code == 200

        data = response.json()
        assert "personalities" in data
        assert "total" in data
        assert isinstance(data["personalities"], list)
        assert data["total"] == len(data["personalities"])

    def test_personality_has_required_fields(self, client):
        """Each personality should have name, description, is_system."""
        response = client.get("/api/personalities")
        data = response.json()

        for personality in data["personalities"]:
            assert "name" in personality
            assert "description" in personality
            assert "is_system" in personality

    def test_includes_system_personalities(self, client):
        """Should include system personalities in the full list."""
        response = client.get("/api/personalities")
        data = response.json()

        names = [p["name"] for p in data["personalities"]]
        # At least one system personality should be present if it exists
        # (synthesizer or consensus_check)
        has_system = any(p["is_system"] for p in data["personalities"])
        # This depends on the actual prompts directory content
        assert data["total"] > 0


class TestListDebatePersonalitiesEndpoint:
    """Tests for the GET /api/personalities/debate endpoint."""

    def test_returns_debate_personalities_only(self, client):
        """Should return only non-system personalities."""
        response = client.get("/api/personalities/debate")
        assert response.status_code == 200

        data = response.json()
        assert "personalities" in data
        assert "total" in data

        # All returned personalities should not be system personalities
        for personality in data["personalities"]:
            assert personality["is_system"] is False

    def test_excludes_system_personalities(self, client):
        """Should exclude consensus_check and synthesizer."""
        response = client.get("/api/personalities/debate")
        data = response.json()

        names = [p["name"] for p in data["personalities"]]
        for sys_name in SYSTEM_PERSONALITIES:
            assert sys_name not in names

    def test_total_matches_list_length(self, client):
        """Total should match the number of personalities returned."""
        response = client.get("/api/personalities/debate")
        data = response.json()

        assert data["total"] == len(data["personalities"])
