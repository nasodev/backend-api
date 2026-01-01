"""Members API 통합 테스트"""

import pytest
from uuid import uuid4


class TestMembersAPI:
    """Members 엔드포인트 테스트"""

    def test_get_members_returns_empty_list(
        self, client_with_fake_member_service
    ):
        """초기 상태에서 빈 목록 반환"""
        response = client_with_fake_member_service.get("/calendar/members")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_members_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/calendar/members")
        assert response.status_code == 403

    def test_create_member_success(
        self, client_with_fake_member_service
    ):
        """구성원 생성 성공"""
        response = client_with_fake_member_service.post(
            "/calendar/members",
            json={"display_name": "테스트", "color": "#FF0000"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["display_name"] == "테스트"
        assert data["color"] == "#FF0000"
        assert data["email"] == "테스트@kidchat.local"

    def test_create_member_duplicate_error(
        self, client_with_fake_member_service, fake_member_service
    ):
        """중복 구성원 생성 시 에러"""
        fake_member_service.add_member("테스트", "#FF0000")

        response = client_with_fake_member_service.post(
            "/calendar/members",
            json={"display_name": "테스트", "color": "#00FF00"},
        )
        assert response.status_code == 400
        assert "이미 등록된" in response.json()["detail"]

    def test_update_member_success(
        self, client_with_fake_member_service, fake_member_service
    ):
        """구성원 수정 성공"""
        member = fake_member_service.add_member("테스트", "#FF0000")

        response = client_with_fake_member_service.patch(
            f"/calendar/members/{member.id}",
            json={"color": "#00FF00"},
        )
        assert response.status_code == 200
        assert response.json()["color"] == "#00FF00"

    def test_update_member_not_found(
        self, client_with_fake_member_service
    ):
        """존재하지 않는 구성원 수정 시 404"""
        response = client_with_fake_member_service.patch(
            f"/calendar/members/{uuid4()}",
            json={"color": "#00FF00"},
        )
        assert response.status_code == 404

    def test_delete_member_success(
        self, client_with_fake_member_service, fake_member_service
    ):
        """구성원 삭제 성공"""
        member = fake_member_service.add_member("테스트", "#FF0000")

        response = client_with_fake_member_service.delete(
            f"/calendar/members/{member.id}"
        )
        assert response.status_code == 204

    def test_delete_member_not_found(
        self, client_with_fake_member_service
    ):
        """존재하지 않는 구성원 삭제 시 404"""
        response = client_with_fake_member_service.delete(
            f"/calendar/members/{uuid4()}"
        )
        assert response.status_code == 404
