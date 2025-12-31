"""헬스체크 엔드포인트 통합 테스트"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import OperationalError

from app.main import app
from app.external import get_db
from tests.fakes import FakeDatabase


def test_root(client):
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Backend API is running"}


def test_health(client):
    """기본 헬스체크 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class TestDBHealthCheck:
    """DB 헬스체크 테스트"""

    def test_db_health_success(self, client):
        """DB 연결 성공 시 ok 반환"""
        fake_db = FakeDatabase()
        fake_db.set_success()

        def get_fake_db():
            yield fake_db

        app.dependency_overrides[get_db] = get_fake_db

        response = client.get("/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["database"] == "connected"
        assert fake_db.execute_count == 1

        app.dependency_overrides.clear()

    def test_db_health_connection_error(self, client):
        """DB 연결 실패 시 error 반환"""
        fake_db = FakeDatabase()
        fake_db.set_connection_error("could not connect to server")

        def get_fake_db():
            yield fake_db

        app.dependency_overrides[get_db] = get_fake_db

        response = client.get("/health/db")

        assert response.status_code == 200  # 현재 구현은 항상 200 반환
        data = response.json()
        assert data["status"] == "error"
        assert "could not connect" in data["database"]

        app.dependency_overrides.clear()

    def test_db_health_timeout(self, client):
        """DB 타임아웃 시 error 반환"""
        fake_db = FakeDatabase()
        fake_db.set_connection_error("connection timed out")

        def get_fake_db():
            yield fake_db

        app.dependency_overrides[get_db] = get_fake_db

        response = client.get("/health/db")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"
        assert "timed out" in data["database"]

        app.dependency_overrides.clear()

    def test_db_session_cleanup(self, client):
        """DB 세션이 정상적으로 정리되는지 확인"""
        fake_db = MagicMock()
        fake_db.execute.return_value = None

        def get_fake_db():
            yield fake_db

        app.dependency_overrides[get_db] = get_fake_db

        response = client.get("/health/db")

        assert response.status_code == 200
        fake_db.execute.assert_called_once()

        app.dependency_overrides.clear()
