"""가족 구성원 관리 API"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
)
from app.services.calendar import (
    MemberServiceProtocol,
    get_member_service,
    NotFoundError,
    DuplicateError,
)

router = APIRouter(prefix="/members", tags=["calendar"])


@router.get("", response_model=list[FamilyMemberResponse])
def get_members(
    user: FirebaseUser = Depends(get_current_user),
    service: MemberServiceProtocol = Depends(get_member_service),
):
    """가족 구성원 목록 조회"""
    return service.get_all()


@router.post("", response_model=FamilyMemberResponse, status_code=status.HTTP_201_CREATED)
def create_member(
    data: FamilyMemberCreate,
    user: FirebaseUser = Depends(get_current_user),
    service: MemberServiceProtocol = Depends(get_member_service),
):
    """가족 구성원 사전 등록"""
    try:
        return service.create(data)
    except DuplicateError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )


@router.patch("/{member_id}", response_model=FamilyMemberResponse)
def update_member(
    member_id: UUID,
    data: FamilyMemberUpdate,
    user: FirebaseUser = Depends(get_current_user),
    service: MemberServiceProtocol = Depends(get_member_service),
):
    """가족 구성원 정보 수정"""
    try:
        return service.update(member_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_member(
    member_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    service: MemberServiceProtocol = Depends(get_member_service),
):
    """가족 구성원 삭제"""
    try:
        service.delete(member_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
