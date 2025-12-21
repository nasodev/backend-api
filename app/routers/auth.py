from fastapi import APIRouter, Depends

from app.dependencies import get_current_user, FirebaseUser

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
