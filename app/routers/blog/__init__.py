"""블로그 라우터 통합"""

from fastapi import APIRouter, Depends

from app.dependencies import get_blog_admin
from app.dependencies.entities import FirebaseUser
from app.routers.blog import images, posts
from app.schemas import BlogPostSummary, BlogPostDetail
from app.services.blog import BlogServiceProtocol, get_blog_service

router = APIRouter(prefix="/blog")
router.include_router(posts.router)
router.include_router(images.router)


@router.get("/admin/posts", response_model=list[BlogPostSummary], tags=["blog"])
def list_all_posts(
    user: FirebaseUser = Depends(get_blog_admin),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """전체 글 목록 — 비발행 포함 (관리자, 에디터 목록 화면용)"""
    return service.list_all()


@router.get("/admin/posts/{slug}", response_model=BlogPostDetail, tags=["blog"])
def get_any_post(
    slug: str,
    user: FirebaseUser = Depends(get_blog_admin),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """글 상세 — 비발행 포함 (관리자, 에디터 편집 화면용)"""
    return service.get_any(slug)
