"""Tests for shared/repository.py."""

from unittest.mock import MagicMock

from shared.repository import BaseRepository


class TestBaseRepository:
    """Tests for BaseRepository base class."""

    def test_init_stores_db_client(self):
        """Should store the database client in _db attribute."""
        mock_db = MagicMock()
        repo = BaseRepository(mock_db)
        assert repo._db is mock_db

    def test_generic_type_parameter(self):
        """Should work with generic type parameter."""
        from typing import Optional

        class MockModel:
            pass

        class TestRepository(BaseRepository[MockModel]):
            def get_by_id(self, id: str) -> Optional[MockModel]:
                return None

        mock_db = MagicMock()
        repo = TestRepository(mock_db)
        assert repo._db is mock_db

    def test_subclass_can_access_db(self):
        """Subclass should be able to access _db and use it."""
        mock_db = MagicMock()
        mock_db.table.return_value.select.return_value.execute.return_value.data = [
            {"id": "123", "name": "test"}
        ]

        class TestRepository(BaseRepository[dict]):
            def get_all(self) -> list[dict]:
                result = self._db.table("test").select("*").execute()
                return result.data

        repo = TestRepository(mock_db)
        result = repo.get_all()

        assert result == [{"id": "123", "name": "test"}]
        mock_db.table.assert_called_once_with("test")
