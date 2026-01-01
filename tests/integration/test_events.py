"""Events API 통합 테스트"""

from datetime import datetime, timedelta
from uuid import uuid4


class TestEventsAPI:
    """Events 엔드포인트 테스트"""

    def test_get_events_returns_empty_list(
        self, client_with_fake_event_service
    ):
        """초기 상태에서 빈 목록 반환"""
        today = datetime.now().date()
        response = client_with_fake_event_service.get(
            "/calendar/events",
            params={
                "start_date": str(today),
                "end_date": str(today + timedelta(days=30)),
            },
        )
        assert response.status_code == 200
        assert response.json()["events"] == []

    def test_get_events_requires_auth(self, client):
        """인증 없이 접근 불가"""
        response = client.get("/calendar/events")
        assert response.status_code == 403

    def test_get_events_in_date_range(
        self, client_with_fake_event_service, fake_event_service
    ):
        """기간 내 이벤트 조회"""
        today = datetime.now()
        fake_event_service.add_event(
            title="테스트 일정",
            start_time=today,
            end_time=today + timedelta(hours=1),
        )

        response = client_with_fake_event_service.get(
            "/calendar/events",
            params={
                "start_date": str(today.date()),
                "end_date": str((today + timedelta(days=30)).date()),
            },
        )
        assert response.status_code == 200
        events = response.json()["events"]
        assert len(events) == 1
        assert events[0]["title"] == "테스트 일정"

    def test_create_event_success(
        self, client_with_fake_event_service, fake_event_service, fake_user
    ):
        """일정 생성 성공"""
        fake_event_service.register_firebase_uid(fake_user.uid)

        now = datetime.now()
        response = client_with_fake_event_service.post(
            "/calendar/events",
            json={
                "title": "새 일정",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
        )
        assert response.status_code == 201
        assert response.json()["title"] == "새 일정"

    def test_create_event_forbidden_for_unregistered_user(
        self, client_with_fake_event_service
    ):
        """미등록 사용자 일정 생성 시 403"""
        now = datetime.now()
        response = client_with_fake_event_service.post(
            "/calendar/events",
            json={
                "title": "새 일정",
                "start_time": now.isoformat(),
                "end_time": (now + timedelta(hours=1)).isoformat(),
            },
        )
        assert response.status_code == 403

    def test_update_event_success(
        self, client_with_fake_event_service, fake_event_service
    ):
        """일정 수정 성공"""
        now = datetime.now()
        event = fake_event_service.add_event(
            title="테스트 일정",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        response = client_with_fake_event_service.patch(
            f"/calendar/events/{event.id}",
            json={"title": "수정된 일정"},
        )
        assert response.status_code == 200
        assert response.json()["title"] == "수정된 일정"

    def test_update_event_not_found(
        self, client_with_fake_event_service
    ):
        """존재하지 않는 일정 수정 시 404"""
        response = client_with_fake_event_service.patch(
            f"/calendar/events/{uuid4()}",
            json={"title": "수정된 일정"},
        )
        assert response.status_code == 404

    def test_delete_event_success(
        self, client_with_fake_event_service, fake_event_service
    ):
        """일정 삭제 성공"""
        now = datetime.now()
        event = fake_event_service.add_event(
            title="테스트 일정",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        response = client_with_fake_event_service.delete(
            f"/calendar/events/{event.id}"
        )
        assert response.status_code == 204

    def test_delete_event_not_found(
        self, client_with_fake_event_service
    ):
        """존재하지 않는 일정 삭제 시 404"""
        response = client_with_fake_event_service.delete(
            f"/calendar/events/{uuid4()}"
        )
        assert response.status_code == 404
