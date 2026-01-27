"""캘린더 AI 라우터 - 일정 파싱 및 등록"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.dependencies import get_current_user
from app.dependencies.entities import FirebaseUser
from app.schemas.ai import ChatRequest, ChatResponse, ParsedEvent
from app.schemas.calendar import EventCreate
from app.services.claude.dependencies import get_claude_service
from app.services.claude.protocol import AIServiceProtocol
from app.services.claude.personas import PersonaType
from app.services.calendar.dependencies import (
    get_pending_event_service,
    get_event_service,
    get_member_service,
)
from app.services.calendar.protocol import (
    PendingEventServiceProtocol,
    EventServiceProtocol,
    MemberServiceProtocol,
)

router = APIRouter(prefix="/ai", tags=["calendar-ai"])


class CalendarAIRequest(BaseModel):
    """캘린더 AI 파싱 요청"""

    text: str | None = Field(
        default=None,
        max_length=10000,
        description="파싱할 텍스트 (예: '내일 오후 3시 치과 예약')",
    )
    image_base64: str | None = Field(
        default=None,
        max_length=10_000_000,
        description="Base64 인코딩된 이미지 (선택)",
    )


class CalendarAIResponse(BaseModel):
    """캘린더 AI 파싱 응답"""

    success: bool = Field(..., description="파싱 성공 여부")
    pending_id: UUID | None = Field(default=None, description="PendingEvent ID")
    events: list[ParsedEvent] | None = Field(default=None, description="파싱된 일정 목록")
    message: str | None = Field(default=None, description="AI 응답 메시지")
    expires_at: str | None = Field(default=None, description="만료 시간 (ISO format)")
    error: str | None = Field(default=None, description="에러 메시지")


class ConfirmRequest(BaseModel):
    """일정 확인 요청"""

    modifications: list[EventCreate] | None = Field(
        default=None,
        description="수정된 일정 목록 (없으면 원본 사용)",
    )


class ConfirmResponse(BaseModel):
    """일정 확인 응답"""

    success: bool = Field(..., description="등록 성공 여부")
    created_count: int = Field(default=0, description="생성된 일정 수")
    event_ids: list[UUID] = Field(default_factory=list, description="생성된 일정 ID 목록")
    error: str | None = Field(default=None, description="에러 메시지")


@router.post("/parse", response_model=CalendarAIResponse)
async def parse_schedule(
    request: CalendarAIRequest,
    current_user: FirebaseUser = Depends(get_current_user),
    claude_service: AIServiceProtocol = Depends(get_claude_service),
    pending_service: PendingEventServiceProtocol = Depends(get_pending_event_service),
    member_service: MemberServiceProtocol = Depends(get_member_service),
):
    """
    텍스트/이미지에서 일정을 파싱하여 PendingEvent로 저장

    - 달력이 페르소나를 사용하여 AI가 일정 정보를 추출
    - 파싱 결과는 PendingEvent에 저장 (30분 TTL)
    - 클라이언트에서 /confirm 호출 시 실제 Event로 변환
    """
    # 텍스트와 이미지 둘 다 없으면 에러
    if not request.text and not request.image_base64:
        return CalendarAIResponse(
            success=False,
            error="텍스트 또는 이미지 중 하나는 필수입니다",
        )

    # 달력이 호출어 추가 (이미지만 있을 때는 기본 프롬프트 사용)
    if request.text:
        prompt = f"달력아 {request.text}"
    else:
        prompt = "달력아 이 이미지에서 일정을 추출해줘"

    # Claude AI 호출
    response = await claude_service.chat(
        prompt=prompt,
        image_base64=request.image_base64,
    )

    if not response.success:
        return CalendarAIResponse(
            success=False,
            error=response.error or "AI 파싱 실패",
        )

    # 파싱된 일정이 없으면 에러
    if not response.parsed_events:
        return CalendarAIResponse(
            success=False,
            error="일정을 찾을 수 없습니다",
            message=response.ai_message,
        )

    # 사용자의 FamilyMember 조회
    member = member_service.get_by_firebase_uid(current_user.uid)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="가족 구성원으로 등록되지 않았습니다. 먼저 /calendar/auth/verify를 호출하세요.",
        )

    # PendingEvent 생성
    pending = pending_service.create(
        event_data=response.parsed_events,
        user_uid=current_user.uid,
        source_text=request.text or "[이미지]",
        source_image_hash=None,  # TODO: 이미지 해시 계산
        ai_message=response.ai_message,
    )

    # ParsedEvent 변환
    parsed_events = [
        ParsedEvent(
            title=e.get("title", ""),
            start_time=e.get("start_time"),
            end_time=e.get("end_time"),
            all_day=e.get("all_day", False),
            description=e.get("description"),
            recurrence=e.get("recurrence"),
        )
        for e in response.parsed_events
    ]

    return CalendarAIResponse(
        success=True,
        pending_id=pending.id,
        events=parsed_events,
        message=response.ai_message,
        expires_at=pending.expires_at.isoformat(),
    )


@router.post("/confirm/{pending_id}", response_model=ConfirmResponse)
async def confirm_schedule(
    pending_id: UUID,
    request: ConfirmRequest | None = None,
    current_user: FirebaseUser = Depends(get_current_user),
    pending_service: PendingEventServiceProtocol = Depends(get_pending_event_service),
):
    """
    PendingEvent를 확인하고 실제 Event로 변환

    - pending_id: 파싱 응답에서 받은 ID
    - modifications: 수정된 일정 목록 (선택)
    """
    try:
        created_events = pending_service.confirm(
            pending_id=pending_id,
            user_uid=current_user.uid,
            modifications=request.modifications if request else None,
        )

        return ConfirmResponse(
            success=True,
            created_count=len(created_events),
            event_ids=[e.id for e in created_events],
        )
    except ValueError as e:
        return ConfirmResponse(
            success=False,
            error=str(e),
        )


@router.post("/cancel/{pending_id}")
async def cancel_schedule(
    pending_id: UUID,
    current_user: FirebaseUser = Depends(get_current_user),
    pending_service: PendingEventServiceProtocol = Depends(get_pending_event_service),
):
    """PendingEvent 취소"""
    try:
        pending_service.cancel(
            pending_id=pending_id,
            user_uid=current_user.uid,
        )
        return {"success": True, "message": "일정이 취소되었습니다"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/pending")
async def list_pending_events(
    current_user: FirebaseUser = Depends(get_current_user),
    pending_service: PendingEventServiceProtocol = Depends(get_pending_event_service),
):
    """사용자의 대기 중인 PendingEvent 목록 조회"""
    pending_events = pending_service.get_pending_by_user(current_user.uid)

    return {
        "count": len(pending_events),
        "pending_events": [
            {
                "id": p.id,
                "events": p.event_data,
                "message": p.ai_message,
                "created_at": p.created_at.isoformat(),
                "expires_at": p.expires_at.isoformat(),
            }
            for p in pending_events
        ],
    }
