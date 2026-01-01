"""Events API 통합 테스트"""

from datetime import datetime, timedelta


class TestEventsAPI:
    """Events 엔드포인트 테스트"""

    def test_get_events_returns_empty_list(self, client_with_fake_auth):
        """초기 상태에서 빈 목록 반환"""
        today = datetime.now().date()
        response = client_with_fake_auth.get(
            "/events",
            params={
                "start_date": str(today),
                "end_date": str(today + timedelta(days=30))
            }
        )
        assert response.status_code == 200
        assert response.json()["events"] == []

    def test_get_events_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/events")
        assert response.status_code == 403
