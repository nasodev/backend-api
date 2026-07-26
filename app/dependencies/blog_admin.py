"""블로그 관리자 인증 의존성"""

from fastapi import Depends, HTTPException, status

from app.config import get_settings
from app.dependencies.auth import get_current_user
from app.dependencies.entities import FirebaseUser


def require_blog_admin(user: FirebaseUser, admin_uids: list[str]) -> FirebaseUser:
    """순수 함수 — 테스트 용이성을 위해 분리"""
    if user.uid not in admin_uids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Blog admin privileges required",
        )
    return user


def get_blog_admin(
    user: FirebaseUser = Depends(get_current_user),
) -> FirebaseUser:
    """
    Usage:
        @router.post("/posts")
        def create(user: FirebaseUser = Depends(get_blog_admin)):
            ...
    """
    settings = get_settings()
    return require_blog_admin(user, settings.blog_admin_uids)
