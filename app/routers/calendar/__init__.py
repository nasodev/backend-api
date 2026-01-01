"""캘린더 라우터 모듈"""

from fastapi import APIRouter

from app.routers.calendar import auth, members, categories, events

router = APIRouter(prefix="/calendar", tags=["calendar"])

router.include_router(auth.router)
router.include_router(members.router)
router.include_router(categories.router)
router.include_router(events.router)

__all__ = ["router"]
