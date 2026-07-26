"""블로그 라우터 통합"""

from fastapi import APIRouter

from app.routers.blog import posts

router = APIRouter(prefix="/blog")
router.include_router(posts.router)
