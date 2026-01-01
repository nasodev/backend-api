"""일정 관리 API"""

from datetime import date

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.dependencies import get_current_user, FirebaseUser
from app.schemas.calendar import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
)
from app.services.calendar import (
    EventServiceProtocol,
    get_event_service,
    NotFoundError,
    ForbiddenError,
)

router = APIRouter(prefix="/events", tags=["calendar"])


@router.get("", response_model=EventListResponse)
def get_events(
    start_date: date = Query(..., description="조회 시작일"),
    end_date: date = Query(..., description="조회 종료일"),
    user: FirebaseUser = Depends(get_current_user),
    service: EventServiceProtocol = Depends(get_event_service),
):
    """일정 목록 조회 (기간 내)"""
    events = service.get_by_date_range(start_date, end_date)
    return EventListResponse(events=events)


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    user: FirebaseUser = Depends(get_current_user),
    service: EventServiceProtocol = Depends(get_event_service),
):
    """일정 생성"""
    try:
        return service.create(data, user.uid)
    except ForbiddenError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.message,
        )


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    user: FirebaseUser = Depends(get_current_user),
    service: EventServiceProtocol = Depends(get_event_service),
):
    """일정 수정"""
    try:
        return service.update(event_id, data)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    service: EventServiceProtocol = Depends(get_event_service),
):
    """일정 삭제"""
    try:
        service.delete(event_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.message,
        )
