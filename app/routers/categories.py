"""카테고리 관리 API"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, FirebaseUser
from app.external.database import get_db
from app.models import Category
from app.schemas import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryResponse])
def get_categories(
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """카테고리 목록 조회"""
    categories = db.query(Category).all()
    return categories


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """카테고리 생성"""
    category = Category(
        name=data.name,
        color=data.color,
        icon=data.icon,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    data: CategoryUpdate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """카테고리 수정"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="카테고리를 찾을 수 없습니다"
        )

    if data.name is not None:
        category.name = data.name
    if data.color is not None:
        category.color = data.color
    if data.icon is not None:
        category.icon = data.icon

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """카테고리 삭제"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="카테고리를 찾을 수 없습니다"
        )

    db.delete(category)
    db.commit()
