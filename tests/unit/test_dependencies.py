"""의존성 모듈 단위 테스트"""

import pytest
from unittest.mock import patch

from app.dependencies.entities import FirebaseUser
from app.dependencies.token_verifier import get_token_verifier


class TestFirebaseUser:
    """FirebaseUser 엔티티 테스트"""

    def test_repr(self):
        """__repr__ 메서드 테스트"""
        user = FirebaseUser(
            uid="test-uid",
            email="test@example.com",
            name="Test User",
            token_data={"uid": "test-uid"},
        )

        repr_str = repr(user)

        assert "FirebaseUser" in repr_str
        assert "test-uid" in repr_str
        assert "test@example.com" in repr_str
        assert "Test User" in repr_str


class TestTokenVerifier:
    """토큰 검증 의존성 테스트"""

    def test_get_token_verifier_returns_function(self):
        """get_token_verifier가 함수를 반환하는지 확인"""
        verifier = get_token_verifier()

        assert callable(verifier)
