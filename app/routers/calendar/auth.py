"""캘린더 인증 API"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas import AuthVerifyResponse
from app.services.calendar import (
    MemberServiceProtocol,
    get_member_service,
)

router = APIRouter(prefix="/auth", tags=["calendar"])


@router.get("/verify", response_model=AuthVerifyResponse)
def verify_calendar_member(
    user: FirebaseUser = Depends(get_current_user),
    service: MemberServiceProtocol = Depends(get_member_service),
):
    """캘린더 가족 구성원 확인 및 연결

    Firebase 인증된 사용자가 캘린더 가족 구성원으로 등록되어 있는지 확인합니다.
    이메일로 사전 등록된 구성원을 찾아 Firebase UID를 연결합니다.
    """
    member = service.verify_and_link(user.email, user.uid)

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="등록되지 않은 가족입니다. 관리자에게 문의하세요.",
        )

    return AuthVerifyResponse(valid=True, member=member)
