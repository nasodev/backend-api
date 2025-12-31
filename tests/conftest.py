"""공통 pytest fixtures"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.claude.dependencies import get_claude_service
from app.dependencies.auth import get_current_user
from app.dependencies.token_verifier import get_token_verifier
from app.dependencies.entities import FirebaseUser
from tests.fakes import FakeAuthService, FakeClaudeService


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트"""
    return TestClient(app)


@pytest.fixture
def fake_auth():
    """Fake 인증 서비스"""
    return FakeAuthService()


@pytest.fixture
def fake_claude():
    """Fake Claude 서비스"""
    return FakeClaudeService()


@pytest.fixture
def fake_user():
    """테스트용 기본 사용자"""
    return FirebaseUser(
        uid="test-uid",
        email="test@example.com",
        name="Test User",
        token_data={"uid": "test-uid", "email": "test@example.com"},
    )


@pytest.fixture
def client_with_fake_claude(fake_claude):
    """Claude 서비스가 Fake로 대체된 테스트 클라이언트"""
    app.dependency_overrides[get_claude_service] = lambda: fake_claude
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_fake_auth(fake_user):
    """인증이 Fake로 대체된 테스트 클라이언트"""
    app.dependency_overrides[get_current_user] = lambda: fake_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_fakes(fake_claude, fake_user):
    """Claude와 Auth 모두 Fake로 대체된 테스트 클라이언트

    Note: fake_claude fixture를 함께 사용하면 같은 인스턴스 공유됨
    """
    async def get_fake_claude():
        return fake_claude

    app.dependency_overrides[get_claude_service] = get_fake_claude
    app.dependency_overrides[get_current_user] = lambda: fake_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def client_with_fake_token_verifier(fake_auth):
    """토큰 검증이 Fake로 대체된 테스트 클라이언트

    Usage:
        def test_auth_success(client_with_fake_token_verifier, fake_auth):
            fake_auth.set_success("user-123", "user@example.com")
            response = client_with_fake_token_verifier.get(
                "/auth/me",
                headers={"Authorization": "Bearer any-token"}
            )
            assert response.status_code == 200
    """
    app.dependency_overrides[get_token_verifier] = lambda: fake_auth.verify_token
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
