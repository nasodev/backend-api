"""블로그 글 API"""

from fastapi import APIRouter, Depends, Query, status

from app.dependencies import get_blog_admin
from app.dependencies.entities import FirebaseUser
from app.schemas import (
    BlogPostCreate,
    BlogPostUpdate,
    BlogPostSummary,
    BlogPostDetail,
    ViewCountResponse,
)
from app.services.blog import BlogServiceProtocol, get_blog_service

router = APIRouter(prefix="/posts", tags=["blog"])


@router.get("", response_model=list[BlogPostSummary])
def list_posts(
    tag: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=100, ge=1, le=1000),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """발행된 글 목록 (본문 제외)"""
    return service.list_published(tag=tag, page=page, size=size)


@router.get("/{slug}", response_model=BlogPostDetail)
def get_post(
    slug: str,
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """글 상세 (발행된 글만)"""
    return service.get_published(slug)


@router.post("/{slug}/view", response_model=ViewCountResponse)
def increment_view(
    slug: str,
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """조회수 +1"""
    return ViewCountResponse(view_count=service.increment_view(slug))


@router.post("", response_model=BlogPostDetail, status_code=status.HTTP_201_CREATED)
def create_post(
    data: BlogPostCreate,
    user: FirebaseUser = Depends(get_blog_admin),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """글 생성 (관리자)"""
    return service.create(data)


@router.put("/{slug}", response_model=BlogPostDetail)
def update_post(
    slug: str,
    data: BlogPostUpdate,
    user: FirebaseUser = Depends(get_blog_admin),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """글 수정 (관리자)"""
    return service.update(slug, data)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    slug: str,
    user: FirebaseUser = Depends(get_blog_admin),
    service: BlogServiceProtocol = Depends(get_blog_service),
):
    """글 삭제 (관리자)"""
    service.delete(slug)
