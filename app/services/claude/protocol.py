"""Claude 서비스 인터페이스 정의"""

from typing import Protocol
from dataclasses import dataclass, field


@dataclass
class ChatResponse:
    """AI 채팅 응답 데이터"""

    output: str
    elapsed_ms: int
    success: bool
    error: str | None = None
    persona_name: str | None = None
    # 캘린더 AI 응답용
    parsed_events: list[dict] | None = None
    ai_message: str | None = None


class AIServiceProtocol(Protocol):
    """AI 서비스 인터페이스 (TDD용 추상화)"""

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
        image_base64: str | None = None,
    ) -> ChatResponse:
        """
        AI 채팅 요청

        Args:
            prompt: 사용자 프롬프트
            timeout_seconds: 타임아웃 (초)
            image_base64: Base64 인코딩된 이미지 (선택)

        Returns:
            ChatResponse: 응답 데이터
        """
        ...
