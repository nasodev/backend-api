"""Fake Claude 서비스"""

from app.services.claude import ChatResponse, AIServiceProtocol


class FakeClaudeService:
    """테스트용 Fake Claude 서비스 (AIServiceProtocol 구현)"""

    def __init__(
        self,
        response: str = "Fake response",
        elapsed_ms: int = 100,
        persona_name: str = "말랑이",
    ):
        self.response = response
        self.elapsed_ms = elapsed_ms
        self.persona_name = persona_name
        self._should_fail = False
        self._error_message = None
        self._call_count = 0
        self._last_prompt = None
        self._last_image_base64 = None
        self._parsed_events: list[dict] | None = None
        self._ai_message: str | None = None

    def set_success(
        self,
        response: str,
        elapsed_ms: int = 100,
        persona_name: str = "말랑이",
        parsed_events: list[dict] | None = None,
        ai_message: str | None = None,
    ):
        """성공 응답 설정"""
        self.response = response
        self.elapsed_ms = elapsed_ms
        self.persona_name = persona_name
        self._should_fail = False
        self._parsed_events = parsed_events
        self._ai_message = ai_message

    def set_failure(self, error_message: str):
        """실패 응답 설정"""
        self._should_fail = True
        self._error_message = error_message

    def set_no_trigger(self):
        """트리거 없음 응답 설정"""
        self._should_fail = True
        self._error_message = "No AI trigger detected"

    def set_timeout(self, timeout_seconds: int = 120):
        """타임아웃 응답 설정"""
        self._should_fail = True
        self._error_message = f"Request timed out after {timeout_seconds} seconds"

    def set_calendar_response(
        self,
        events: list[dict],
        message: str,
        elapsed_ms: int = 100,
    ):
        """달력이 응답 설정"""
        import json
        self.response = json.dumps({"events": events, "message": message})
        self.elapsed_ms = elapsed_ms
        self.persona_name = "달력이"
        self._should_fail = False
        self._parsed_events = events
        self._ai_message = message

    @property
    def call_count(self) -> int:
        """호출 횟수"""
        return self._call_count

    @property
    def last_prompt(self) -> str | None:
        """마지막 호출 프롬프트"""
        return self._last_prompt

    @property
    def last_image_base64(self) -> str | None:
        """마지막 호출 이미지"""
        return self._last_image_base64

    async def chat(
        self,
        prompt: str,
        timeout_seconds: int | None = None,
        image_base64: str | None = None,
    ) -> ChatResponse:
        """채팅 요청 (Fake)"""
        self._call_count += 1
        self._last_prompt = prompt
        self._last_image_base64 = image_base64

        if self._should_fail:
            return ChatResponse(
                output="",
                elapsed_ms=self.elapsed_ms,
                success=False,
                error=self._error_message,
                persona_name=self.persona_name if "trigger" not in (self._error_message or "") else None,
            )

        return ChatResponse(
            output=self.response,
            elapsed_ms=self.elapsed_ms,
            success=True,
            persona_name=self.persona_name,
            parsed_events=self._parsed_events,
            ai_message=self._ai_message,
        )
