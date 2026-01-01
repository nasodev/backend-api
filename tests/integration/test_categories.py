"""Categories API 통합 테스트"""


class TestCategoriesAPI:
    """Categories 엔드포인트 테스트"""

    def test_get_categories_returns_empty_list(self, client_with_fake_auth):
        """초기 상태에서 빈 목록 반환"""
        response = client_with_fake_auth.get("/categories")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_categories_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/categories")
        assert response.status_code == 403
