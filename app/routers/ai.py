import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.claude.dependencies import get_claude_service
from app.services.claude.protocol import AIServiceProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: FirebaseUser = Depends(get_current_user),
    claude_service: AIServiceProtocol = Depends(get_claude_service),
):
    """
    Claude에게 프롬프트를 보내고 응답을 받습니다.

    Firebase 인증 필수.

    ## AI 캐릭터 호출 방법
    - "말랑아 ..." → 말랑이 (다정한 친구)
    - "루팡아 ..." → 루팡 (건방진 친구)
    - "푸딩아 ..." → 푸딩 (애완동물 느낌)
    - "마이콜아 ..." → 마이콜 (영어 선생님)
    - "에이아이야 ..." → 말랑이 (기존 호환)
    """
    logger.info(f"Chat request from user {user.uid}, prompt length: {len(request.prompt)}")

    result = await claude_service.chat(
        prompt=request.prompt,
        timeout_seconds=request.timeout_seconds,
    )

    if not result.success:
        if "no ai trigger" in (result.error or "").lower():
            # AI 호출어가 없는 경우 - 일반 메시지이므로 무시
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "No AI trigger detected",
                    "error_type": "no_trigger",
                    "detail": "메시지에 AI 호출어가 없습니다. (말랑아/루팡아/푸딩아/마이콜아)",
                },
            )
        elif "timed out" in (result.error or "").lower():
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail={
                    "error": "Request timed out",
                    "error_type": "timeout",
                    "detail": result.error,
                },
            )
        elif "not found" in (result.error or "").lower():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "AI service unavailable",
                    "error_type": "service_unavailable",
                    "detail": result.error,
                },
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "AI processing failed",
                    "error_type": "cli_error",
                    "detail": result.error,
                },
            )

    return ChatResponse(
        response=result.output,
        elapsed_time_ms=result.elapsed_ms,
        truncated=False,
        persona=result.persona_name,
    )
