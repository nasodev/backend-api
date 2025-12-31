"""AI 채팅 엔드포인트 통합 테스트"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.claude.dependencies import get_claude_service
from app.dependencies.auth import get_current_user
from app.dependencies.entities import FirebaseUser
from tests.fakes import FakeClaudeService


class TestAIChatEndpoint:
    """AI 채팅 엔드포인트 테스트 (DI 방식)"""

    def test_chat_success(self, client_with_fakes, fake_claude):
        """유효한 요청으로 Claude 응답 반환"""
        fake_claude.set_success(
            response="안녕! 뭐 물어볼 거 있어?",
            elapsed_ms=1500,
            persona_name="말랑이",
        )

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "말랑아 안녕하세요"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "안녕! 뭐 물어볼 거 있어?"
        assert data["elapsed_time_ms"] == 1500
        assert data["truncated"] is False
        assert data["persona"] == "말랑이"

    def test_chat_timeout(self, client_with_fakes, fake_claude):
        """타임아웃 시 408 반환"""
        fake_claude.set_timeout(timeout_seconds=120)

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "말랑아 복잡한 질문"},
        )

        assert response.status_code == 408
        data = response.json()["detail"]
        assert data["error_type"] == "timeout"

    def test_chat_cli_error(self, client_with_fakes, fake_claude):
        """CLI 에러 시 500 반환"""
        fake_claude.set_failure("Some CLI error")

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "말랑아 test"},
        )

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_type"] == "cli_error"

    def test_chat_service_unavailable(self, client_with_fakes, fake_claude):
        """Claude CLI 없을 때 503 반환"""
        fake_claude.set_failure("Claude CLI not found at: claude")

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "말랑아 test"},
        )

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["error_type"] == "service_unavailable"

    def test_chat_no_trigger(self, client_with_fakes, fake_claude):
        """AI 호출어 없는 메시지 시 400 반환"""
        fake_claude.set_no_trigger()

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "그냥 일반 메시지"},
        )

        assert response.status_code == 400
        data = response.json()["detail"]
        assert data["error_type"] == "no_trigger"

    def test_chat_no_auth(self, client):
        """인증 없이 요청 시 403 반환"""
        response = client.post(
            "/ai/chat",
            json={"prompt": "hello"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    def test_chat_empty_prompt(self, client_with_fake_auth):
        """빈 프롬프트 시 422 반환"""
        response = client_with_fake_auth.post(
            "/ai/chat",
            json={"prompt": ""},
        )
        assert response.status_code == 422

    def test_chat_prompt_too_long(self, client_with_fake_auth):
        """프롬프트 10000자 초과 시 422 반환"""
        response = client_with_fake_auth.post(
            "/ai/chat",
            json={"prompt": "a" * 10001},
        )
        assert response.status_code == 422

    def test_chat_custom_timeout(self, client_with_fakes, fake_claude):
        """커스텀 타임아웃 전달 확인"""
        fake_claude.set_success(response="response", elapsed_ms=1000)

        response = client_with_fakes.post(
            "/ai/chat",
            json={"prompt": "말랑아 test", "timeout_seconds": 60},
        )

        assert response.status_code == 200
        # FakeClaudeService에서 마지막 호출 정보 확인
        assert fake_claude.call_count == 1
        assert "말랑아 test" in fake_claude.last_prompt

    def test_chat_multiple_personas(self, client_with_fakes, fake_claude):
        """다양한 페르소나 응답 테스트"""
        personas = [
            ("말랑아 hi", "말랑이"),
            ("루팡아 hi", "루팡"),
            ("푸딩아 hi", "푸딩"),
            ("마이콜아 hi", "마이콜"),
        ]

        for prompt, expected_persona in personas:
            fake_claude.set_success(
                response=f"Hello from {expected_persona}",
                persona_name=expected_persona,
            )

            response = client_with_fakes.post(
                "/ai/chat",
                json={"prompt": prompt},
            )

            assert response.status_code == 200
            assert response.json()["persona"] == expected_persona
