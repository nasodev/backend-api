"""Claude Code CLI 서비스 구현"""

import asyncio
import base64
import json
import os
import re
import tempfile
import time
import logging
from typing import Any

from app.config import get_settings
from app.services.claude.protocol import ChatResponse
from app.services.claude.personas import (
    PersonaType,
    detect_persona,
    get_system_prompt,
    get_persona,
)

logger = logging.getLogger(__name__)


class ClaudeService:
    """Claude Code CLI 서비스 (AIServiceProtocol 구현)"""

    def __init__(self):
        self.settings = get_settings()

    def _build_prompt(
        self, user_prompt: str, persona_type: PersonaType, image_path: str | None = None
    ) -> str:
        """사용자 프롬프트에 페르소나 시스템 지시사항 추가"""
        system_prompt = get_system_prompt(persona_type)

        # 이미지가 있으면 프롬프트에 경로 추가
        if image_path:
            return f"{user_prompt}\n\n이미지: {image_path}\n\n{system_prompt}"
        return f"{user_prompt}\n\n{system_prompt}"

    def _save_temp_image(self, image_base64: str) -> str:
        """Base64 이미지를 임시 파일로 저장하고 경로 반환"""
        # data:image/png;base64, 접두어 제거
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        image_data = base64.b64decode(image_base64)

        # 임시 파일 생성 (확장자는 png로 기본 설정)
        fd, temp_path = tempfile.mkstemp(suffix=".png")
        try:
            os.write(fd, image_data)
        finally:
            os.close(fd)

        return temp_path

    def _parse_calendar_response(self, output: str) -> tuple[list[dict], str | None]:
        """달력이 페르소나 응답에서 JSON 파싱"""
        try:
            # JSON 블록 추출 (```json ... ``` 또는 순수 JSON)
            json_match = re.search(r"```json\s*(.*?)\s*```", output, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 순수 JSON 시도
                json_str = output.strip()

            data = json.loads(json_str)

            events = data.get("events", [])
            message = data.get("message")

            return events, message
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to parse calendar response: {e}")
            return [], None

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
        image_base64: str | None = None,
    ) -> ChatResponse:
        """
        Claude CLI로 채팅 요청

        메시지에서 자동으로 페르소나를 감지합니다:
        - "말랑아 ..." → 말랑이 (다정한 친구)
        - "루팡아 ..." → 루팡 (건방진 친구)
        - "푸딩아 ..." → 푸딩 (애완동물 느낌)
        - "마이콜아 ..." → 마이콜 (영어 선생님)
        - "달력아 ..." → 달력이 (일정 파싱 전용)
        - "에이아이야 ..." → 말랑이 (기존 호환)

        Args:
            prompt: 사용자 프롬프트 (호출어 포함)
            timeout_seconds: 타임아웃 (초)
            image_base64: Base64 인코딩된 이미지 (선택)

        Returns:
            ChatResponse: 응답 또는 에러
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
            return ChatResponse(
                output="",
                elapsed_ms=0,
                success=False,
                error="No AI trigger detected",
            )

        persona = get_persona(persona_type)

        # 이미지 처리
        temp_image_path = None
        if image_base64:
            try:
                temp_image_path = self._save_temp_image(image_base64)
                logger.info(f"Saved temp image: {temp_image_path}")
            except Exception as e:
                logger.error(f"Failed to save temp image: {e}")
                return ChatResponse(
                    output="",
                    elapsed_ms=0,
                    success=False,
                    error=f"Failed to process image: {e}",
                    persona_name=persona.display_name,
                )

        try:
            full_prompt = self._build_prompt(actual_prompt, persona_type, temp_image_path)

            cmd = [
                settings.claude_cli_path,
                "--dangerously-skip-permissions",
                "-p",
                full_prompt,
            ]

            logger.info(
                f"Executing Claude CLI with persona={persona.display_name}, "
                f"timeout={timeout}s, has_image={temp_image_path is not None}"
            )
            start_time = time.monotonic()

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
                return ChatResponse(
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
                return ChatResponse(
                    output="",
                    elapsed_ms=elapsed_ms,
                    success=False,
                    error=error_msg or f"CLI exited with code {process.returncode}",
                    persona_name=persona.display_name,
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            logger.info(
                f"Claude CLI success ({persona.display_name}) in {elapsed_ms}ms, "
                f"output length: {len(output)}"
            )

            # 달력이 페르소나인 경우 JSON 파싱
            parsed_events = None
            ai_message = None
            if persona_type == PersonaType.CALENDAR:
                parsed_events, ai_message = self._parse_calendar_response(output)
                logger.info(f"Parsed {len(parsed_events)} events from calendar response")

            return ChatResponse(
                output=output,
                elapsed_ms=elapsed_ms,
                success=True,
                persona_name=persona.display_name,
                parsed_events=parsed_events,
                ai_message=ai_message,
            )

        except FileNotFoundError:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            error = f"Claude CLI not found at: {settings.claude_cli_path}"
            logger.error(error)
            return ChatResponse(
                output="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=error,
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.exception("Unexpected error in Claude CLI execution")
            return ChatResponse(
                output="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=str(e),
            )
        finally:
            # 임시 이미지 파일 정리
            if temp_image_path and os.path.exists(temp_image_path):
                try:
                    os.remove(temp_image_path)
                    logger.debug(f"Removed temp image: {temp_image_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove temp image: {e}")
