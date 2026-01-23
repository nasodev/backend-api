"""Calendar AI 통합 테스트"""

import pytest
from fastapi.testclient import TestClient
from uuid import uuid4

from app.main import app
from app.dependencies import get_current_user
from app.dependencies.entities import FirebaseUser
from app.services.claude.dependencies import get_claude_service
from app.services.calendar.dependencies import (
    get_member_service,
    get_pending_event_service,
)
from tests.fakes.fake_claude import FakeClaudeService
from tests.fakes.fake_calendar import FakeMemberService, FakePendingEventService


@pytest.fixture
def fake_user():
    return FirebaseUser(
        uid="test-uid",
        email="test@example.com",
        name="Test User",
        token_data={},
    )


@pytest.fixture
def fake_claude():
    return FakeClaudeService()


@pytest.fixture
def fake_member_service():
    service = FakeMemberService()
    # 테스트 유저 추가
    service.add_member(
        display_name="Test User",
        firebase_uid="test-uid",
        is_registered=True,
    )
    return service


@pytest.fixture
def fake_pending_service():
    return FakePendingEventService()


@pytest.fixture
def client_with_fakes(
    fake_user, fake_claude, fake_member_service, fake_pending_service
):
    app.dependency_overrides[get_current_user] = lambda: fake_user
    app.dependency_overrides[get_claude_service] = lambda: fake_claude
    app.dependency_overrides[get_member_service] = lambda: fake_member_service
    app.dependency_overrides[get_pending_event_service] = lambda: fake_pending_service

    yield TestClient(app)

    app.dependency_overrides.clear()


class TestCalendarAIParse:
    """POST /calendar/ai/parse 테스트"""

    def test_parse_success(
        self, client_with_fakes, fake_claude, fake_member_service
    ):
        """일정 파싱 성공"""
        fake_claude.set_calendar_response(
            events=[
                {
                    "title": "치과 예약",
                    "start_time": "2026-01-23T15:00:00",
                    "end_time": "2026-01-23T16:00:00",
                    "all_day": False,
                }
            ],
            message="내일 3시 치과 예약이에요!",
        )

        response = client_with_fakes.post(
            "/calendar/ai/parse",
            json={"text": "내일 오후 3시 치과"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["pending_id"] is not None
        assert len(data["events"]) == 1
        assert data["events"][0]["title"] == "치과 예약"
        assert data["message"] == "내일 3시 치과 예약이에요!"

    def test_parse_with_image(self, client_with_fakes, fake_claude):
        """이미지 포함 파싱"""
        fake_claude.set_calendar_response(
            events=[
                {
                    "title": "회의",
                    "start_time": "2026-01-24T10:00:00",
                    "end_time": "2026-01-24T11:00:00",
                    "all_day": False,
                }
            ],
            message="이미지에서 회의 일정을 찾았어요!",
        )

        # Base64 인코딩된 1x1 PNG
        test_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        response = client_with_fakes.post(
            "/calendar/ai/parse",
            json={
                "text": "이 이미지에서 일정 찾아줘",
                "image_base64": test_image,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert fake_claude.last_image_base64 == test_image

    def test_parse_no_events_found(self, client_with_fakes, fake_claude):
        """일정을 찾지 못한 경우"""
        fake_claude.set_success(
            response="일정 정보를 찾을 수 없습니다.",
            persona_name="달력이",
            parsed_events=None,
        )

        response = client_with_fakes.post(
            "/calendar/ai/parse",
            json={"text": "안녕하세요"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "일정을 찾을 수 없습니다" in data["error"]

    def test_parse_ai_failure(self, client_with_fakes, fake_claude):
        """AI 호출 실패"""
        fake_claude.set_failure("Claude API error")

        response = client_with_fakes.post(
            "/calendar/ai/parse",
            json={"text": "내일 치과"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Claude API error" in data["error"]

    def test_parse_unregistered_user(self, client_with_fakes, fake_claude, fake_member_service):
        """등록되지 않은 사용자"""
        # 기존 멤버 제거
        fake_member_service._firebase_uid_map.clear()
        fake_member_service._members.clear()

        fake_claude.set_calendar_response(
            events=[{"title": "테스트", "start_time": "2026-01-23T10:00:00", "end_time": "2026-01-23T11:00:00", "all_day": False}],
            message="테스트",
        )

        response = client_with_fakes.post(
            "/calendar/ai/parse",
            json={"text": "내일 치과"},
        )

        assert response.status_code == 404
        assert "가족 구성원으로 등록되지 않았습니다" in response.json()["detail"]


class TestCalendarAIConfirm:
    """POST /calendar/ai/confirm/{pending_id} 테스트"""

    def test_confirm_success(self, client_with_fakes, fake_pending_service):
        """일정 확인 성공"""
        # PendingEvent 생성
        pending = fake_pending_service.create(
            event_data=[
                {
                    "title": "치과",
                    "start_time": "2026-01-23T15:00:00",
                    "end_time": "2026-01-23T16:00:00",
                    "all_day": False,
                }
            ],
            user_uid="test-uid",
            ai_message="치과 예약",
        )

        response = client_with_fakes.post(f"/calendar/ai/confirm/{pending.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["created_count"] == 1
        assert len(data["event_ids"]) == 1

    def test_confirm_not_found(self, client_with_fakes):
        """존재하지 않는 PendingEvent"""
        response = client_with_fakes.post(f"/calendar/ai/confirm/{uuid4()}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()


class TestCalendarAICancel:
    """POST /calendar/ai/cancel/{pending_id} 테스트"""

    def test_cancel_success(self, client_with_fakes, fake_pending_service):
        """일정 취소 성공"""
        pending = fake_pending_service.create(
            event_data=[{"title": "테스트", "start_time": "2026-01-23T10:00:00", "end_time": "2026-01-23T11:00:00", "all_day": False}],
            user_uid="test-uid",
        )

        response = client_with_fakes.post(f"/calendar/ai/cancel/{pending.id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # 상태 확인
        assert fake_pending_service.get_by_id(pending.id).status == "cancelled"

    def test_cancel_not_found(self, client_with_fakes):
        """존재하지 않는 PendingEvent 취소"""
        response = client_with_fakes.post(f"/calendar/ai/cancel/{uuid4()}")

        assert response.status_code == 400


class TestCalendarAIPending:
    """GET /calendar/ai/pending 테스트"""

    def test_list_pending_events(self, client_with_fakes, fake_pending_service):
        """대기 중인 일정 목록 조회"""
        # PendingEvent 2개 생성
        fake_pending_service.create(
            event_data=[{"title": "일정1", "start_time": "2026-01-23T10:00:00", "end_time": "2026-01-23T11:00:00", "all_day": False}],
            user_uid="test-uid",
        )
        fake_pending_service.create(
            event_data=[{"title": "일정2", "start_time": "2026-01-24T10:00:00", "end_time": "2026-01-24T11:00:00", "all_day": False}],
            user_uid="test-uid",
        )

        response = client_with_fakes.get("/calendar/ai/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert len(data["pending_events"]) == 2

    def test_list_pending_empty(self, client_with_fakes):
        """대기 중인 일정 없음"""
        response = client_with_fakes.get("/calendar/ai/pending")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert len(data["pending_events"]) == 0
