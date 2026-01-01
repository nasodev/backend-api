"""Calendar Auth 통합 테스트"""


class TestCalendarAuth:
    """캘린더 인증 테스트"""

    def test_verify_returns_member_info(self, client_with_fake_auth):
        """인증 성공 시 가족 구성원 정보 반환"""
        # TODO: member 생성 후 테스트
        response = client_with_fake_auth.get("/auth/calendar/verify")
        # 등록되지 않은 경우 403
        assert response.status_code == 403
