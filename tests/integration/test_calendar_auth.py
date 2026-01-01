"""Calendar Auth 통합 테스트"""


class TestCalendarAuth:
    """캘린더 인증 테스트"""

    def test_verify_unregistered_returns_403(
        self, client_with_fake_member_service
    ):
        """미등록 사용자 접근 시 403"""
        response = client_with_fake_member_service.get("/calendar/auth/verify")
        assert response.status_code == 403
        assert "등록되지 않은 가족" in response.json()["detail"]

    def test_verify_registered_returns_member_info(
        self, client_with_fake_member_service, fake_member_service, fake_user
    ):
        """등록된 사용자 접근 시 멤버 정보 반환"""
        # 사전 등록된 멤버 추가 (이메일로 매칭)
        fake_member_service.add_member(
            display_name="테스트",
            color="#FF0000",
        )
        # 이메일 직접 설정 (fake_user.email과 매칭되도록)
        member_id = list(fake_member_service._members.keys())[0]
        member = fake_member_service._members[member_id]
        from app.schemas.calendar import FamilyMemberResponse

        fake_member_service._members[member_id] = FamilyMemberResponse(
            id=member.id,
            email=fake_user.email,
            display_name=member.display_name,
            color=member.color,
            is_registered=member.is_registered,
            created_at=member.created_at,
        )

        response = client_with_fake_member_service.get("/calendar/auth/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["member"]["display_name"] == "테스트"

    def test_verify_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/calendar/auth/verify")
        assert response.status_code == 403
