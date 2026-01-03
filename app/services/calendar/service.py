"""캘린더 서비스 구현"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import FamilyMember, Category, Event
from app.schemas.calendar import (
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    EventCreate,
    EventUpdate,
    EventResponse,
    MemberInfo,
    CategoryInfo,
)


class NotFoundError(Exception):
    """리소스를 찾을 수 없음"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class DuplicateError(Exception):
    """중복된 리소스"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class ForbiddenError(Exception):
    """권한 없음"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class MemberService:
    """가족 구성원 서비스 (MemberServiceProtocol 구현)"""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _name_to_email(name: str) -> str:
        """이름을 이메일 형식으로 변환"""
        return f"{name}@kidchat.local"

    def get_all(self) -> list[FamilyMemberResponse]:
        """모든 구성원 조회"""
        members = self.db.query(FamilyMember).all()
        return [FamilyMemberResponse.model_validate(m) for m in members]

    def create(self, data: FamilyMemberCreate) -> FamilyMemberResponse:
        """구성원 생성"""
        email = self._name_to_email(data.display_name)

        existing = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.email == email)
            .first()
        )
        if existing:
            raise DuplicateError("이미 등록된 구성원입니다")

        member = FamilyMember(
            email=email,
            display_name=data.display_name,
            color=data.color,
            is_registered=False,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return FamilyMemberResponse.model_validate(member)

    def update(
        self, member_id: UUID, data: FamilyMemberUpdate
    ) -> FamilyMemberResponse:
        """구성원 수정"""
        member = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.id == member_id)
            .first()
        )
        if not member:
            raise NotFoundError("구성원을 찾을 수 없습니다")

        if data.display_name is not None:
            member.display_name = data.display_name
            member.email = self._name_to_email(data.display_name)
        if data.color is not None:
            member.color = data.color

        self.db.commit()
        self.db.refresh(member)
        return FamilyMemberResponse.model_validate(member)

    def delete(self, member_id: UUID) -> None:
        """구성원 삭제"""
        member = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.id == member_id)
            .first()
        )
        if not member:
            raise NotFoundError("구성원을 찾을 수 없습니다")

        self.db.delete(member)
        self.db.commit()

    def get_by_firebase_uid(self, firebase_uid: str) -> FamilyMemberResponse | None:
        """Firebase UID로 구성원 조회"""
        member = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.firebase_uid == firebase_uid)
            .first()
        )
        if not member:
            return None
        return FamilyMemberResponse.model_validate(member)

    def verify_and_link(
        self, email: str, firebase_uid: str
    ) -> FamilyMemberResponse:
        """Firebase UID로 구성원 찾거나 자동 생성"""
        # 1. Firebase UID로 기존 구성원 검색
        member = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.firebase_uid == firebase_uid)
            .first()
        )

        # 2. 없으면 자동 생성 (첫 로그인)
        if not member:
            display_name = email.split("@")[0]
            member = FamilyMember(
                email=email,
                display_name=display_name,
                firebase_uid=firebase_uid,
                is_registered=True,
            )
            self.db.add(member)
            self.db.commit()
            self.db.refresh(member)

        return FamilyMemberResponse.model_validate(member)


class CategoryService:
    """카테고리 서비스 (CategoryServiceProtocol 구현)"""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> list[CategoryResponse]:
        """모든 카테고리 조회"""
        categories = self.db.query(Category).all()
        return [CategoryResponse.model_validate(c) for c in categories]

    def create(self, data: CategoryCreate) -> CategoryResponse:
        """카테고리 생성"""
        category = Category(
            name=data.name,
            color=data.color,
            icon=data.icon,
        )
        self.db.add(category)
        self.db.commit()
        self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    def update(
        self, category_id: UUID, data: CategoryUpdate
    ) -> CategoryResponse:
        """카테고리 수정"""
        category = (
            self.db.query(Category)
            .filter(Category.id == category_id)
            .first()
        )
        if not category:
            raise NotFoundError("카테고리를 찾을 수 없습니다")

        if data.name is not None:
            category.name = data.name
        if data.color is not None:
            category.color = data.color
        if data.icon is not None:
            category.icon = data.icon

        self.db.commit()
        self.db.refresh(category)
        return CategoryResponse.model_validate(category)

    def delete(self, category_id: UUID) -> None:
        """카테고리 삭제"""
        category = (
            self.db.query(Category)
            .filter(Category.id == category_id)
            .first()
        )
        if not category:
            raise NotFoundError("카테고리를 찾을 수 없습니다")

        self.db.delete(category)
        self.db.commit()


class EventService:
    """일정 서비스 (EventServiceProtocol 구현)"""

    def __init__(self, db: Session):
        self.db = db

    def _event_to_response(
        self, event: Event, occurrence_date: date = None
    ) -> EventResponse:
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
            )
            if event.category
            else None,
            is_recurring=event.recurrence_rule is not None,
            occurrence_date=occurrence_date,
            created_at=event.created_at,
            updated_at=event.updated_at,
        )

    def _get_member_by_firebase_uid(self, firebase_uid: str) -> FamilyMember:
        """Firebase UID로 가족 구성원 조회"""
        member = (
            self.db.query(FamilyMember)
            .filter(FamilyMember.firebase_uid == firebase_uid)
            .first()
        )
        if not member:
            raise ForbiddenError("등록되지 않은 가족입니다")
        return member

    def get_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[EventResponse]:
        """기간 내 일정 조회"""
        events = (
            self.db.query(Event)
            .filter(
                Event.start_time >= datetime.combine(start_date, datetime.min.time()),
                Event.start_time <= datetime.combine(end_date, datetime.max.time()),
            )
            .all()
        )
        return [self._event_to_response(e) for e in events]

    def create(
        self, data: EventCreate, creator_firebase_uid: str
    ) -> EventResponse:
        """일정 생성"""
        member = self._get_member_by_firebase_uid(creator_firebase_uid)

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
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)
        return self._event_to_response(event)

    def update(self, event_id: UUID, data: EventUpdate) -> EventResponse:
        """일정 수정"""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundError("일정을 찾을 수 없습니다")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(event, field, value)

        self.db.commit()
        self.db.refresh(event)
        return self._event_to_response(event)

    def delete(self, event_id: UUID) -> None:
        """일정 삭제"""
        event = self.db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise NotFoundError("일정을 찾을 수 없습니다")

        self.db.delete(event)
        self.db.commit()
