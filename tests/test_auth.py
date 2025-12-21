from unittest.mock import patch
from fastapi.testclient import TestClient
from firebase_admin import auth as firebase_auth

from app.main import app

client = TestClient(app)


class TestAuthEndpoints:
    """인증 엔드포인트 테스트"""

    @patch("app.dependencies.verify_id_token")
    def test_auth_me_success(self, mock_verify):
        """유효한 토큰으로 /auth/me 요청 시 사용자 정보 반환"""
        mock_verify.return_value = {
            "uid": "test-uid-123",
            "email": "test@example.com",
            "name": "Test User",
        }

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "test-uid-123"
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"

    @patch("app.dependencies.verify_id_token")
    def test_auth_verify_success(self, mock_verify):
        """유효한 토큰으로 /auth/verify 요청 시 valid: true 반환"""
        mock_verify.return_value = {
            "uid": "test-uid-123",
            "email": "test@example.com",
        }

        response = client.get(
            "/auth/verify",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["uid"] == "test-uid-123"

    def test_auth_me_no_token(self):
        """토큰 없이 /auth/me 요청 시 403 반환"""
        response = client.get("/auth/me")

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_auth_verify_no_token(self):
        """토큰 없이 /auth/verify 요청 시 403 반환"""
        response = client.get("/auth/verify")

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    @patch("app.dependencies.verify_id_token")
    def test_auth_me_invalid_token(self, mock_verify):
        """잘못된 토큰으로 요청 시 401 반환"""
        mock_verify.side_effect = firebase_auth.InvalidIdTokenError("Invalid token")

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"

    @patch("app.dependencies.verify_id_token")
    def test_auth_me_expired_token(self, mock_verify):
        """만료된 토큰으로 요청 시 401 반환"""
        mock_verify.side_effect = firebase_auth.ExpiredIdTokenError(
            "Token expired", cause=None
        )

        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer expired-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"
