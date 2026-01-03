"""Calendar Auth 통합 테스트"""


class TestCalendarAuth:
    """캘린더 인증 테스트"""

    def test_verify_auto_registers_new_user(
        self, client_with_fake_member_service, fake_user
    ):
        """첫 로그인 시 자동 등록"""
        response = client_with_fake_member_service.get("/calendar/auth/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        # 이메일에서 @ 앞부분이 display_name으로 설정됨
        assert data["member"]["display_name"] == fake_user.email.split("@")[0]
        assert data["member"]["email"] == fake_user.email

    def test_verify_returns_existing_member(
        self, client_with_fake_member_service, fake_member_service, fake_user
    ):
        """기존 등록 사용자는 기존 정보 반환"""
        # 사전 등록된 멤버 추가 (firebase_uid로 매칭)
        fake_member_service.add_member(
            display_name="기존유저",
            color="#FF0000",
            firebase_uid=fake_user.uid,
            is_registered=True,
        )

        response = client_with_fake_member_service.get("/calendar/auth/verify")
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["member"]["display_name"] == "기존유저"
        assert data["member"]["color"] == "#FF0000"

    def test_verify_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/calendar/auth/verify")
        assert response.status_code == 403
