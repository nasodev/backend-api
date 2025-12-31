"""인증 엔드포인트 통합 테스트"""

import pytest


class TestAuthEndpoints:
    """인증 엔드포인트 테스트 (DI 방식)"""

    def test_auth_me_success(self, client_with_fake_token_verifier, fake_auth):
        """유효한 토큰으로 /auth/me 요청 시 사용자 정보 반환"""
        fake_auth.set_success(
            uid="test-uid-123",
            email="test@example.com",
            name="Test User",
        )

        response = client_with_fake_token_verifier.get(
            "/auth/me",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["uid"] == "test-uid-123"
        assert data["email"] == "test@example.com"
        assert data["name"] == "Test User"

    def test_auth_verify_success(self, client_with_fake_token_verifier, fake_auth):
        """유효한 토큰으로 /auth/verify 요청 시 valid: true 반환"""
        fake_auth.set_success(
            uid="test-uid-123",
            email="test@example.com",
        )

        response = client_with_fake_token_verifier.get(
            "/auth/verify",
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["uid"] == "test-uid-123"

    def test_auth_me_no_token(self, client):
        """토큰 없이 /auth/me 요청 시 403 반환"""
        response = client.get("/auth/me")

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_auth_verify_no_token(self, client):
        """토큰 없이 /auth/verify 요청 시 403 반환"""
        response = client.get("/auth/verify")

        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_auth_me_invalid_token(self, client_with_fake_token_verifier, fake_auth):
        """잘못된 토큰으로 요청 시 401 반환"""
        fake_auth.set_failure("invalid")

        response = client_with_fake_token_verifier.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"

    def test_auth_me_expired_token(self, client_with_fake_token_verifier, fake_auth):
        """만료된 토큰으로 요청 시 401 반환"""
        fake_auth.set_failure("expired")

        response = client_with_fake_token_verifier.get(
            "/auth/me",
            headers={"Authorization": "Bearer expired-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Token has expired"

    def test_auth_me_auth_error(self, client_with_fake_token_verifier, fake_auth):
        """인증 서비스 오류 시 401 반환"""
        fake_auth.set_failure("auth_error")

        response = client_with_fake_token_verifier.get(
            "/auth/me",
            headers={"Authorization": "Bearer some-token"},
        )

        assert response.status_code == 401
        assert "Authentication failed" in response.json()["detail"]

    def test_auth_verify_invalid_token(self, client_with_fake_token_verifier, fake_auth):
        """유효하지 않은 토큰으로 /auth/verify 요청 시 401 반환"""
        fake_auth.set_failure("invalid")

        response = client_with_fake_token_verifier.get(
            "/auth/verify",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid authentication token"
