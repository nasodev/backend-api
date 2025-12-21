from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


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


class ChatResponse(BaseModel):
    """AI Chat 응답 스키마"""

    response: str = Field(..., description="Claude 응답")
    elapsed_time_ms: int = Field(..., description="응답 시간 (밀리초)")
    truncated: bool = Field(default=False, description="응답 잘림 여부")

    model_config = ConfigDict(from_attributes=True)
