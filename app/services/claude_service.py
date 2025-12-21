import asyncio
import time
import logging
from dataclasses import dataclass

from app.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Claude CLI 응답 데이터"""

    output: str
    elapsed_ms: int
    success: bool
    error: str | None = None


class ClaudeService:
    """Claude Code CLI 서비스"""

    SYSTEM_INSTRUCTIONS = """
## Instructions
- 간결하게 친구처럼 대답한다
- 파일을 수정하면 안된다
- 100단어 이내로 대답한다
- 최신정보가 필요하면 웹검색을 한다
"""

    def __init__(self):
        self.settings = get_settings()

    def _build_prompt(self, user_prompt: str) -> str:
        """사용자 프롬프트에 시스템 지시사항 추가"""
        return f"{user_prompt}\n\n{self.SYSTEM_INSTRUCTIONS}"

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
    ) -> ClaudeResponse:
        """
        Claude CLI로 채팅 요청

        Args:
            prompt: 사용자 프롬프트
            timeout_seconds: 타임아웃 (초)

        Returns:
            ClaudeResponse: 응답 또는 에러
        """
        settings = self.settings
        timeout = min(
            timeout_seconds or settings.claude_timeout_seconds,
            settings.claude_max_timeout_seconds,
        )

        full_prompt = self._build_prompt(prompt)

        cmd = [
            settings.claude_cli_path,
            "--dangerously-skip-permissions",
            "-p",
            full_prompt,
        ]

        logger.info(f"Executing Claude CLI with timeout={timeout}s")
        start_time = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                elapsed_ms = int((time.monotonic() - start_time) * 1000)
                logger.warning(f"Claude CLI timeout after {elapsed_ms}ms")
                return ClaudeResponse(
                    output="",
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error=f"Request timed out after {timeout} seconds",
                )

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            if process.returncode != 0:
                error_msg = stderr.decode("utf-8", errors="replace").strip()
                logger.error(f"Claude CLI error: {error_msg}")
                return ClaudeResponse(
                    output="",
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error=error_msg or f"CLI exited with code {process.returncode}",
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            logger.info(f"Claude CLI success in {elapsed_ms}ms, output length: {len(output)}")

            return ClaudeResponse(
                output=output,
                elapsed_ms=elapsed_ms,
                success=True,
            )

        except FileNotFoundError:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            error = f"Claude CLI not found at: {settings.claude_cli_path}"
            logger.error(error)
            return ClaudeResponse(
                output="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=error,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Unexpected error in Claude CLI execution")
            return ClaudeResponse(
                output="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=str(e),
            )


_claude_service: ClaudeService | None = None


def get_claude_service() -> ClaudeService:
    """Claude 서비스 싱글톤 반환"""
    global _claude_service
    if _claude_service is None:
        _claude_service = ClaudeService()
    return _claude_service
