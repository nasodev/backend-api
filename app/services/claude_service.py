"""Claude Code CLI 서비스"""

import asyncio
import time
import logging
from dataclasses import dataclass

from app.config import get_settings
from app.services.personas import (
    PersonaType,
    detect_persona,
    get_system_prompt,
    get_persona,
)

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Claude CLI 응답 데이터"""

    output: str
    elapsed_ms: int
    success: bool
    error: str | None = None
    persona_name: str | None = None  # 응답한 캐릭터 이름


class ClaudeService:
    """Claude Code CLI 서비스"""

    def __init__(self):
        self.settings = get_settings()

    def _build_prompt(self, user_prompt: str, persona_type: PersonaType) -> str:
        """사용자 프롬프트에 페르소나 시스템 지시사항 추가"""
        system_prompt = get_system_prompt(persona_type)
        return f"{user_prompt}\n\n{system_prompt}"

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
    ) -> ClaudeResponse:
        """
        Claude CLI로 채팅 요청

        메시지에서 자동으로 페르소나를 감지합니다:
        - "말랑아 ..." → 말랑이 (다정한 친구)
        - "루팡아 ..." → 루팡 (건방진 친구)
        - "푸딩아 ..." → 푸딩 (애완동물 느낌)
        - "마이콜아 ..." → 마이콜 (영어 선생님)
        - "에이아이야 ..." → 말랑이 (기존 호환)

        Args:
            prompt: 사용자 프롬프트 (호출어 포함)
            timeout_seconds: 타임아웃 (초)

        Returns:
            ClaudeResponse: 응답 또는 에러
        """
        settings = self.settings
        timeout = min(
            timeout_seconds or settings.claude_timeout_seconds,
            settings.claude_max_timeout_seconds,
        )

        # 페르소나 감지
        persona_type, actual_prompt = detect_persona(prompt)

        if persona_type is None:
            # 호출어가 없으면 AI 응답 안함
            return ClaudeResponse(
                output="",
                elapsed_ms=0,
                success=False,
                error="No AI trigger detected",
            )

        persona = get_persona(persona_type)
        full_prompt = self._build_prompt(actual_prompt, persona_type)

        cmd = [
            settings.claude_cli_path,
            "--dangerously-skip-permissions",
            "-p",
            full_prompt,
        ]

        logger.info(
            f"Executing Claude CLI with persona={persona.display_name}, timeout={timeout}s"
        )
        start_time = time.monotonic()

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
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
                    persona_name=persona.display_name,
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
                    persona_name=persona.display_name,
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            logger.info(
                f"Claude CLI success ({persona.display_name}) in {elapsed_ms}ms, output length: {len(output)}"
            )

            return ClaudeResponse(
                output=output,
                elapsed_ms=elapsed_ms,
                success=True,
                persona_name=persona.display_name,
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
