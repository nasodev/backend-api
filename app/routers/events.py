"""일정 관리 API"""

from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, FirebaseUser
from app.external.database import get_db
from app.models import Event, FamilyMember, Category
from app.schemas.calendar import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventListResponse,
    MemberInfo,
    CategoryInfo,
)

router = APIRouter(prefix="/events", tags=["events"])


def get_member_by_firebase_uid(db: Session, firebase_uid: str) -> FamilyMember:
    """Firebase UID로 가족 구성원 조회"""
    member = db.query(FamilyMember).filter(
        FamilyMember.firebase_uid == firebase_uid
    ).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="등록되지 않은 가족입니다"
        )
    return member


def event_to_response(event: Event, occurrence_date: date = None) -> EventResponse:
    """Event 모델을 응답 스키마로 변환"""
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        start_time=event.start_time,
        end_time=event.end_time,
        all_day=event.all_day,
        member=MemberInfo(
            name=event.creator.display_name,
            color=event.creator.color,
        ),
        category=CategoryInfo(
            name=event.category.name,
            color=event.category.color,
        ) if event.category else None,
        is_recurring=event.recurrence_rule is not None,
        occurrence_date=occurrence_date,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.get("", response_model=EventListResponse)
def get_events(
    start_date: date = Query(..., description="조회 시작일"),
    end_date: date = Query(..., description="조회 종료일"),
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일정 목록 조회 (기간 내)"""
    # TODO: 반복 일정 전개 로직 추가
    events = db.query(Event).filter(
        Event.start_time >= datetime.combine(start_date, datetime.min.time()),
        Event.start_time <= datetime.combine(end_date, datetime.max.time()),
    ).all()

    return EventListResponse(
        events=[event_to_response(e) for e in events]
    )


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    data: EventCreate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일정 생성"""
    member = get_member_by_firebase_uid(db, user.uid)

    event = Event(
        title=data.title,
        description=data.description,
        start_time=data.start_time,
        end_time=data.end_time,
        all_day=data.all_day,
        category_id=data.category_id,
        created_by=member.id,
        recurrence_rule=data.recurrence_rule,
        recurrence_start=data.recurrence_start,
        recurrence_end=data.recurrence_end,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event_to_response(event)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    data: EventUpdate,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일정 수정"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일정을 찾을 수 없습니다"
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(event, field, value)

    db.commit()
    db.refresh(event)
    return event_to_response(event)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """일정 삭제"""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="일정을 찾을 수 없습니다"
        )

    db.delete(event)
    db.commit()
