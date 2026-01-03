"""캘린더 인증 API"""

from fastapi import APIRouter, Depends

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
    """캘린더 가족 구성원 확인 및 자동 등록

    Firebase 인증된 사용자를 캘린더 구성원으로 확인합니다.
    첫 로그인 시 자동으로 구성원으로 등록됩니다.
    """
    member = service.verify_and_link(user.email, user.uid)
    return AuthVerifyResponse(valid=True, member=member)
