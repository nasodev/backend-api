"""Categories API 통합 테스트"""

from uuid import uuid4


class TestCategoriesAPI:
    """Categories 엔드포인트 테스트"""

    def test_get_categories_returns_empty_list(
        self, client_with_fake_category_service
    ):
        """초기 상태에서 빈 목록 반환"""
        response = client_with_fake_category_service.get("/calendar/categories")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_categories_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/calendar/categories")
        assert response.status_code == 403

    def test_create_category_success(
        self, client_with_fake_category_service
    ):
        """카테고리 생성 성공"""
        response = client_with_fake_category_service.post(
            "/calendar/categories",
            json={"name": "학교", "color": "#FF0000", "icon": "school"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "학교"
        assert data["color"] == "#FF0000"
        assert data["icon"] == "school"

    def test_update_category_success(
        self, client_with_fake_category_service, fake_category_service
    ):
        """카테고리 수정 성공"""
        category = fake_category_service.add_category("학교", "#FF0000")

        response = client_with_fake_category_service.patch(
            f"/calendar/categories/{category.id}",
            json={"color": "#00FF00"},
        )
        assert response.status_code == 200
        assert response.json()["color"] == "#00FF00"

    def test_update_category_not_found(
        self, client_with_fake_category_service
    ):
        """존재하지 않는 카테고리 수정 시 404"""
        response = client_with_fake_category_service.patch(
            f"/calendar/categories/{uuid4()}",
            json={"color": "#00FF00"},
        )
        assert response.status_code == 404

    def test_delete_category_success(
        self, client_with_fake_category_service, fake_category_service
    ):
        """카테고리 삭제 성공"""
        category = fake_category_service.add_category("학교", "#FF0000")

        response = client_with_fake_category_service.delete(
            f"/calendar/categories/{category.id}"
        )
        assert response.status_code == 204

    def test_delete_category_not_found(
        self, client_with_fake_category_service
    ):
        """존재하지 않는 카테고리 삭제 시 404"""
        response = client_with_fake_category_service.delete(
            f"/calendar/categories/{uuid4()}"
        )
        assert response.status_code == 404
