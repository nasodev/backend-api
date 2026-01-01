"""Members API 통합 테스트"""

import pytest
from uuid import uuid4


class TestMembersAPI:
    """Members 엔드포인트 테스트"""

    def test_get_members_returns_empty_list(self, client_with_fake_auth):
        """초기 상태에서 빈 목록 반환"""
        response = client_with_fake_auth.get("/members")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_members_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/members")
        assert response.status_code == 403
