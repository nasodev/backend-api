"""Claude 서비스 인터페이스 정의"""

from typing import Protocol
from dataclasses import dataclass


@dataclass
class ChatResponse:
    """AI 채팅 응답 데이터"""

    output: str
    elapsed_ms: int
    success: bool
    error: str | None = None
    persona_name: str | None = None


class AIServiceProtocol(Protocol):
    """AI 서비스 인터페이스 (TDD용 추상화)"""

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
    ) -> ChatResponse:
        """
        AI 채팅 요청

        Args:
            prompt: 사용자 프롬프트
            timeout_seconds: 타임아웃 (초)

        Returns:
            ChatResponse: 응답 데이터
        """
        ...
