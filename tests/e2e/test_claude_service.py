"""Claude Service E2E 테스트

실제 Claude CLI를 사용하는 테스트입니다.
Claude CLI가 설치되어 있어야 하며, API 비용이 발생합니다.

Usage:
    pytest -m e2e tests/e2e/test_claude_service.py -v
"""

import shutil
import pytest

from app.services.claude.service import ClaudeService


# Claude CLI 설치 여부 확인
CLAUDE_CLI_AVAILABLE = shutil.which("claude") is not None


@pytest.mark.e2e
@pytest.mark.skipif(not CLAUDE_CLI_AVAILABLE, reason="Claude CLI not installed")
class TestClaudeServiceE2E:
    """ClaudeService 실제 CLI 테스트"""

    @pytest.fixture
    def service(self):
        """ClaudeService 인스턴스"""
        return ClaudeService()

    @pytest.mark.asyncio
    async def test_chat_with_mallangi(self, service):
        """말랑이 페르소나로 실제 대화"""
        response = await service.chat(
            prompt="말랑아 1+1은?",
            timeout_seconds=30,
        )

        assert response.success is True
        assert response.persona_name == "말랑이"
        assert len(response.output) > 0
        assert response.elapsed_ms > 0

    @pytest.mark.asyncio
    async def test_chat_with_lupin(self, service):
        """루팡 페르소나로 실제 대화"""
        response = await service.chat(
            prompt="루팡아 안녕",
            timeout_seconds=30,
        )

        assert response.success is True
        assert response.persona_name == "루팡"
        assert len(response.output) > 0

    @pytest.mark.asyncio
    async def test_chat_no_trigger(self, service):
        """호출어 없는 메시지는 AI 응답 안함"""
        response = await service.chat(
            prompt="그냥 일반 메시지",
            timeout_seconds=10,
        )

        assert response.success is False
        assert "No AI trigger" in response.error

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_chat_timeout(self, service):
        """타임아웃 테스트 (매우 짧은 타임아웃)"""
        response = await service.chat(
            prompt="말랑아 아주 긴 이야기를 해줘",
            timeout_seconds=1,  # 1초면 거의 확실히 타임아웃
        )

        # 타임아웃 발생 시 success=False
        if not response.success:
            assert "timed out" in response.error.lower()
