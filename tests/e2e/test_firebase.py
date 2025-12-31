"""Firebase E2E 테스트

실제 Firebase 인증을 사용하는 테스트입니다.

== 방법 1: API Key 사용 (전체 인증 플로우) ==
.env에 다음 설정이 필요합니다:
- TEST_FIREBASE_ID: 테스트 계정 이메일
- TEST_FIREBASE_PASSWORD: 테스트 계정 비밀번호
- FIREBASE_API_KEY: Firebase 프로젝트 API 키

== 방법 2: Service Account만 사용 (기본) ==
firebase_credentials_path만 있으면 됩니다.

Usage:
    pytest -m e2e tests/e2e/test_firebase.py -v
"""

import pytest
import httpx
from pathlib import Path

from app.config import get_settings
from app.external.firebase import get_firebase_app, verify_id_token


settings = get_settings()

# Firebase credentials 파일 존재 여부
FIREBASE_CREDENTIALS_AVAILABLE = Path(settings.firebase_credentials_path).exists()

# 전체 인증 플로우 테스트 가능 여부 (API Key 필요)
FIREBASE_FULL_TEST_AVAILABLE = all([
    settings.test_firebase_id,
    settings.test_firebase_password,
    settings.test_firebase_api_key,
    FIREBASE_CREDENTIALS_AVAILABLE,
])


async def get_firebase_id_token(email: str, password: str, api_key: str) -> str:
    """Firebase Auth REST API로 ID 토큰 획득"""
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            json={
                "email": email,
                "password": password,
                "returnSecureToken": True,
            },
        )
        response.raise_for_status()
        return response.json()["idToken"]


@pytest.mark.e2e
@pytest.mark.skipif(
    not FIREBASE_CREDENTIALS_AVAILABLE,
    reason="Firebase credentials file not found"
)
class TestFirebaseE2E:
    """Firebase 인증 E2E 테스트 (Service Account만 필요)"""

    @pytest.mark.asyncio
    async def test_firebase_app_initialization(self):
        """Firebase Admin SDK 초기화 테스트"""
        app = get_firebase_app()
        assert app is not None
        assert app.name == "[DEFAULT]"

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """잘못된 토큰 검증 시 에러 발생"""
        from firebase_admin import auth as firebase_auth

        # Firebase 앱 초기화 (필요 시)
        get_firebase_app()

        with pytest.raises(firebase_auth.InvalidIdTokenError):
            verify_id_token("invalid-token-12345")


@pytest.mark.e2e
@pytest.mark.skipif(
    not FIREBASE_FULL_TEST_AVAILABLE,
    reason="Firebase API key or test credentials not configured"
)
class TestFirebaseFullAuthE2E:
    """Firebase 전체 인증 플로우 E2E 테스트 (API Key 필요)"""

    @pytest.mark.asyncio
    async def test_verify_valid_token(self):
        """유효한 토큰 검증 테스트"""
        # 실제 토큰 획득
        id_token = await get_firebase_id_token(
            email=settings.test_firebase_id,
            password=settings.test_firebase_password,
            api_key=settings.test_firebase_api_key,
        )

        # 토큰 검증
        decoded = verify_id_token(id_token)

        assert decoded is not None
        assert "uid" in decoded
        assert decoded.get("email") == settings.test_firebase_id

    @pytest.mark.asyncio
    async def test_full_auth_flow(self):
        """전체 인증 플로우 테스트 (로그인 → API 호출)"""
        from fastapi.testclient import TestClient
        from app.main import app

        # 토큰 획득
        id_token = await get_firebase_id_token(
            email=settings.test_firebase_id,
            password=settings.test_firebase_password,
            api_key=settings.test_firebase_api_key,
        )

        # API 호출
        client = TestClient(app)
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {id_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == settings.test_firebase_id
        assert "uid" in data
