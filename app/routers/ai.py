import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas.ai import ChatRequest, ChatResponse
from app.services.claude_service import get_claude_service, ClaudeService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: FirebaseUser = Depends(get_current_user),
    claude_service: ClaudeService = Depends(get_claude_service),
):
    """
    Claude에게 프롬프트를 보내고 응답을 받습니다.

    Firebase 인증 필수.

    시스템 지시사항 자동 추가:
    - 간결하게 친구처럼 대답
    - 파일 수정 금지
    - 100단어 이내
    - 최신정보 필요시 웹검색
    """
    logger.info(f"Chat request from user {user.uid}, prompt length: {len(request.prompt)}")

    result = await claude_service.chat(
        prompt=request.prompt,
        timeout_seconds=request.timeout_seconds,
    )

    if not result.success:
        if "timed out" in (result.error or "").lower():
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
    )
