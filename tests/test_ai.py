from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.services.claude_service import ClaudeResponse

client = TestClient(app)


class TestAIChatEndpoint:
    """AI 채팅 엔드포인트 테스트"""

    @patch("app.dependencies.verify_id_token")
    @patch("app.services.claude_service.ClaudeService.chat")
    def test_chat_success(self, mock_chat, mock_verify):
        """유효한 요청으로 Claude 응답 반환"""
        mock_verify.return_value = {
            "uid": "test-uid",
            "email": "test@example.com",
        }

        mock_chat.return_value = ClaudeResponse(
            output="안녕! 뭐 물어볼 거 있어?",
            elapsed_ms=1500,
            success=True,
        )

        response = client.post(
            "/ai/chat",
            json={"prompt": "안녕하세요"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["response"] == "안녕! 뭐 물어볼 거 있어?"
        assert data["elapsed_time_ms"] == 1500
        assert data["truncated"] is False

    @patch("app.dependencies.verify_id_token")
    @patch("app.services.claude_service.ClaudeService.chat")
    def test_chat_timeout(self, mock_chat, mock_verify):
        """타임아웃 시 408 반환"""
        mock_verify.return_value = {"uid": "test-uid"}

        mock_chat.return_value = ClaudeResponse(
            output="",
            elapsed_ms=120000,
            success=False,
            error="Request timed out after 120 seconds",
        )

        response = client.post(
            "/ai/chat",
            json={"prompt": "복잡한 질문"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 408
        data = response.json()["detail"]
        assert data["error_type"] == "timeout"

    @patch("app.dependencies.verify_id_token")
    @patch("app.services.claude_service.ClaudeService.chat")
    def test_chat_cli_error(self, mock_chat, mock_verify):
        """CLI 에러 시 500 반환"""
        mock_verify.return_value = {"uid": "test-uid"}

        mock_chat.return_value = ClaudeResponse(
            output="",
            elapsed_ms=500,
            success=False,
            error="Some CLI error",
        )

        response = client.post(
            "/ai/chat",
            json={"prompt": "test"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 500
        data = response.json()["detail"]
        assert data["error_type"] == "cli_error"

    @patch("app.dependencies.verify_id_token")
    @patch("app.services.claude_service.ClaudeService.chat")
    def test_chat_service_unavailable(self, mock_chat, mock_verify):
        """Claude CLI 없을 때 503 반환"""
        mock_verify.return_value = {"uid": "test-uid"}

        mock_chat.return_value = ClaudeResponse(
            output="",
            elapsed_ms=100,
            success=False,
            error="Claude CLI not found at: claude",
        )

        response = client.post(
            "/ai/chat",
            json={"prompt": "test"},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 503
        data = response.json()["detail"]
        assert data["error_type"] == "service_unavailable"

    def test_chat_no_auth(self):
        """인증 없이 요청 시 403 반환"""
        response = client.post(
            "/ai/chat",
            json={"prompt": "hello"},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Not authenticated"

    @patch("app.dependencies.verify_id_token")
    def test_chat_empty_prompt(self, mock_verify):
        """빈 프롬프트 시 422 반환"""
        mock_verify.return_value = {"uid": "test-uid"}

        response = client.post(
            "/ai/chat",
            json={"prompt": ""},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 422

    @patch("app.dependencies.verify_id_token")
    def test_chat_prompt_too_long(self, mock_verify):
        """프롬프트 10000자 초과 시 422 반환"""
        mock_verify.return_value = {"uid": "test-uid"}

        response = client.post(
            "/ai/chat",
            json={"prompt": "a" * 10001},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 422

    @patch("app.dependencies.verify_id_token")
    @patch("app.services.claude_service.ClaudeService.chat")
    def test_chat_custom_timeout(self, mock_chat, mock_verify):
        """커스텀 타임아웃 전달 확인"""
        mock_verify.return_value = {"uid": "test-uid"}

        mock_chat.return_value = ClaudeResponse(
            output="response",
            elapsed_ms=1000,
            success=True,
        )

        response = client.post(
            "/ai/chat",
            json={"prompt": "test", "timeout_seconds": 60},
            headers={"Authorization": "Bearer valid-token"},
        )

        assert response.status_code == 200
        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args[1]
        assert call_kwargs["timeout_seconds"] == 60
