"""카테고리 관리 API"""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)
from app.services.calendar import (
    CategoryServiceProtocol,
    get_category_service,
)

router = APIRouter(prefix="/categories", tags=["calendar"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    user: FirebaseUser = Depends(get_current_user),
    service: CategoryServiceProtocol = Depends(get_category_service),
):
    """카테고리 목록 조회"""
    return service.get_all()


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    user: FirebaseUser = Depends(get_current_user),
    service: CategoryServiceProtocol = Depends(get_category_service),
):
    """카테고리 생성"""
    return service.create(data)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    user: FirebaseUser = Depends(get_current_user),
    service: CategoryServiceProtocol = Depends(get_category_service),
):
    """카테고리 수정"""
    return service.update(category_id, data)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    service: CategoryServiceProtocol = Depends(get_category_service),
):
    """카테고리 삭제"""
    service.delete(category_id)
