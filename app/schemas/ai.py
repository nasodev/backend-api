from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ParsedEvent(BaseModel):
    """AI가 파싱한 일정 데이터"""

    title: str = Field(..., description="일정 제목")
    start_time: datetime = Field(..., description="시작 시간")
    end_time: datetime = Field(..., description="종료 시간")
    all_day: bool = Field(default=False, description="종일 여부")
    description: Optional[str] = Field(default=None, description="설명")
    recurrence: Optional[str] = Field(default=None, description="반복 규칙 (RRULE)")


class ChatRequest(BaseModel):
    """AI Chat 요청 스키마"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Claude에게 보낼 프롬프트",
    )
    timeout_seconds: Optional[int] = Field(
        default=None,
        ge=10,
        le=300,
        description="타임아웃 설정 (10-300초)",
    )
    image_base64: Optional[str] = Field(
        default=None,
        max_length=10_000_000,  # ~7.5MB base64 (5MB 이미지)
        description="Base64 인코딩된 이미지",
    )


class ChatResponse(BaseModel):
    """AI Chat 응답 스키마"""

    response: str = Field(..., description="Claude 응답")
    elapsed_time_ms: int = Field(..., description="응답 시간 (밀리초)")
    truncated: bool = Field(default=False, description="응답 잘림 여부")
    persona: Optional[str] = Field(
        default=None,
        description="응답한 AI 캐릭터 (말랑이/루팡/푸딩/마이콜/달력이)",
    )
    # 캘린더 AI 전용 필드
    action_type: Optional[str] = Field(
        default=None,
        description="액션 타입 (confirm_event, info 등)",
    )
    pending_id: Optional[UUID] = Field(
        default=None,
        description="PendingEvent ID (확인 대기 중인 일정)",
    )
    pending_events: Optional[list[ParsedEvent]] = Field(
        default=None,
        description="파싱된 일정 목록",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="PendingEvent 만료 시간",
    )

    model_config = ConfigDict(from_attributes=True)
