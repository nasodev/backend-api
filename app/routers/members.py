"""가족 구성원 관리 API"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, FirebaseUser
from app.external.database import get_db
from app.models import FamilyMember
from app.schemas import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
)

router = APIRouter(prefix="/members", tags=["members"])


def name_to_email(name: str) -> str:
    """이름을 이메일 형식으로 변환"""
    return f"{name}@kidchat.local"


@router.get("", response_model=list[FamilyMemberResponse])
def get_members(
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """가족 구성원 목록 조회"""
    members = db.query(FamilyMember).all()
    return members


@router.post("", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    data: FamilyMemberCreate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """가족 구성원 사전 등록"""
    email = name_to_email(data.display_name)

    # 중복 확인
    existing = db.query(FamilyMember).filter(FamilyMember.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 구성원입니다"
        )

    member = FamilyMember(
        email=email,
        display_name=data.display_name,
        color=data.color,
        is_registered=False,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.patch("/{member_id}", response_model=FamilyMemberResponse)
def update_member(
    member_id: UUID,
    data: FamilyMemberUpdate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """가족 구성원 정보 수정"""
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구성원을 찾을 수 없습니다"
        )

    if data.display_name is not None:
        member.display_name = data.display_name
        member.email = name_to_email(data.display_name)
    if data.color is not None:
        member.color = data.color

    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """가족 구성원 삭제"""
    member = db.query(FamilyMember).filter(FamilyMember.id == member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="구성원을 찾을 수 없습니다"
        )

    db.delete(member)
    db.commit()
