from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, FirebaseUser
from app.external.database import get_db
from app.models import FamilyMember
from app.schemas import AuthVerifyResponse, FamilyMemberResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me")
def get_me(user: FirebaseUser = Depends(get_current_user)):
    """현재 인증된 사용자 정보 반환"""
    return {
        "uid": user.uid,
        "email": user.email,
        "name": user.name,
    }


@router.get("/verify")
def verify_token(user: FirebaseUser = Depends(get_current_user)):
    """토큰 유효성 확인"""
    return {"valid": True, "uid": user.uid}


@router.get("/calendar/verify", response_model=AuthVerifyResponse)
def verify_calendar_member(
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """캘린더 가족 구성원 확인 및 연결"""
    # 이메일로 사전 등록된 구성원 찾기
    member = db.query(FamilyMember).filter(
        FamilyMember.email == user.email
    ).first()

    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="등록되지 않은 가족입니다. 관리자에게 문의하세요."
        )

    # Firebase UID 연결 (첫 로그인 시)
    if not member.firebase_uid:
        member.firebase_uid = user.uid
        member.is_registered = True
        db.commit()
        db.refresh(member)

    return AuthVerifyResponse(
        valid=True,
        member=FamilyMemberResponse.model_validate(member)
    )
