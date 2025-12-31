"""ClaudeService 단위 테스트 - 에러 경로"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.services.claude.service import ClaudeService


class TestClaudeServiceErrors:
    """ClaudeService 에러 처리 테스트"""

    @pytest.fixture
    def service(self):
        """ClaudeService 인스턴스"""
        return ClaudeService()

    @pytest.mark.asyncio
    async def test_cli_not_found_error(self, service):
        """Claude CLI가 없을 때 FileNotFoundError 처리"""
        with patch.object(service, "settings") as mock_settings:
            mock_settings.claude_cli_path = "/nonexistent/path/to/claude"
            mock_settings.claude_timeout_seconds = 30
            mock_settings.claude_max_timeout_seconds = 120

            response = await service.chat("말랑아 안녕", timeout_seconds=10)

            assert response.success is False
            assert "not found" in response.error.lower()
            assert response.elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_unexpected_exception_handling(self, service):
        """예상치 못한 예외 처리"""
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_exec.side_effect = RuntimeError("Unexpected system error")

            response = await service.chat("말랑아 테스트", timeout_seconds=10)

            assert response.success is False
            assert "Unexpected system error" in response.error
            assert response.elapsed_ms >= 0

    @pytest.mark.asyncio
    async def test_process_non_zero_exit_code(self, service):
        """CLI가 0이 아닌 종료 코드 반환 시"""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"CLI error: invalid argument")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            response = await service.chat("말랑아 테스트", timeout_seconds=10)

            assert response.success is False
            assert "invalid argument" in response.error

    @pytest.mark.asyncio
    async def test_timeout_kills_process(self, service):
        """타임아웃 시 프로세스 종료 확인"""
        import asyncio

        mock_process = AsyncMock()
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()
        mock_process.communicate = AsyncMock(
            side_effect=asyncio.TimeoutError()
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            response = await service.chat("말랑아 테스트", timeout_seconds=1)

            assert response.success is False
            assert "timed out" in response.error.lower()
            mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_stderr_decode_error_handling(self, service):
        """stderr 디코딩 에러 처리 (잘못된 UTF-8)"""
        mock_process = AsyncMock()
        mock_process.returncode = 1
        # Invalid UTF-8 bytes
        mock_process.communicate = AsyncMock(
            return_value=(b"", b"\xff\xfe invalid utf-8")
        )

        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            response = await service.chat("말랑아 테스트", timeout_seconds=10)

            assert response.success is False
            # Should not raise, should handle gracefully
            assert response.error is not None
