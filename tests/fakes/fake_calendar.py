"""Fake 캘린더 서비스"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

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
from app.services.calendar import NotFoundError, DuplicateError, ForbiddenError


class FakeMemberService:
    """테스트용 Fake Member 서비스

    Usage:
        fake_service = FakeMemberService()
        app.dependency_overrides[get_member_service] = lambda: fake_service
    """

    def __init__(self):
        self._members: dict[UUID, FamilyMemberResponse] = {}
        self._firebase_uid_map: dict[str, UUID] = {}

    def _name_to_email(self, name: str) -> str:
        return f"{name}@kidchat.local"

    def add_member(
        self,
        display_name: str,
        color: str = "#FF0000",
        firebase_uid: str | None = None,
        is_registered: bool = False,
    ) -> FamilyMemberResponse:
        """테스트용 멤버 추가"""
        member_id = uuid4()
        member = FamilyMemberResponse(
            id=member_id,
            email=self._name_to_email(display_name),
            display_name=display_name,
            color=color,
            is_registered=is_registered,
            created_at=datetime.now(timezone.utc),
        )
        self._members[member_id] = member
        if firebase_uid:
            self._firebase_uid_map[firebase_uid] = member_id
        return member

    def get_all(self) -> list[FamilyMemberResponse]:
        return list(self._members.values())

    def create(self, data: FamilyMemberCreate) -> FamilyMemberResponse:
        email = self._name_to_email(data.display_name)
        for member in self._members.values():
            if member.email == email:
                raise DuplicateError("이미 등록된 구성원입니다")

        member_id = uuid4()
        member = FamilyMemberResponse(
            id=member_id,
            email=email,
            display_name=data.display_name,
            color=data.color,
            is_registered=False,
            created_at=datetime.now(timezone.utc),
        )
        self._members[member_id] = member
        return member

    def update(
        self, member_id: UUID, data: FamilyMemberUpdate
    ) -> FamilyMemberResponse:
        if member_id not in self._members:
            raise NotFoundError("구성원을 찾을 수 없습니다")

        member = self._members[member_id]
        updated = FamilyMemberResponse(
            id=member.id,
            email=self._name_to_email(data.display_name)
            if data.display_name
            else member.email,
            display_name=data.display_name or member.display_name,
            color=data.color or member.color,
            is_registered=member.is_registered,
            created_at=member.created_at,
        )
        self._members[member_id] = updated
        return updated

    def delete(self, member_id: UUID) -> None:
        if member_id not in self._members:
            raise NotFoundError("구성원을 찾을 수 없습니다")
        del self._members[member_id]

    def get_by_firebase_uid(self, firebase_uid: str) -> FamilyMemberResponse | None:
        member_id = self._firebase_uid_map.get(firebase_uid)
        if member_id:
            return self._members.get(member_id)
        return None

    def verify_and_link(
        self, email: str, firebase_uid: str
    ) -> FamilyMemberResponse:
        """Firebase UID로 구성원 찾거나 자동 생성"""
        # 1. Firebase UID로 검색
        member_id = self._firebase_uid_map.get(firebase_uid)
        if member_id and member_id in self._members:
            return self._members[member_id]

        # 2. 이메일로 검색 후 연결
        for mid, member in self._members.items():
            if member.email == email:
                self._firebase_uid_map[firebase_uid] = mid
                updated = FamilyMemberResponse(
                    id=member.id,
                    email=member.email,
                    display_name=member.display_name,
                    color=member.color,
                    is_registered=True,
                    created_at=member.created_at,
                )
                self._members[mid] = updated
                return updated

        # 3. 없으면 자동 생성
        member_id = uuid4()
        display_name = email.split("@")[0]
        member = FamilyMemberResponse(
            id=member_id,
            email=email,
            display_name=display_name,
            color="#808080",  # 기본 색상
            is_registered=True,
            created_at=datetime.now(timezone.utc),
        )
        self._members[member_id] = member
        self._firebase_uid_map[firebase_uid] = member_id
        return member


class FakeCategoryService:
    """테스트용 Fake Category 서비스

    Usage:
        fake_service = FakeCategoryService()
        app.dependency_overrides[get_category_service] = lambda: fake_service
    """

    def __init__(self):
        self._categories: dict[UUID, CategoryResponse] = {}

    def add_category(
        self, name: str, color: str = "#FF0000", icon: str | None = None
    ) -> CategoryResponse:
        """테스트용 카테고리 추가"""
        category_id = uuid4()
        category = CategoryResponse(
            id=category_id,
            name=name,
            color=color,
            icon=icon,
        )
        self._categories[category_id] = category
        return category

    def get_all(self) -> list[CategoryResponse]:
        return list(self._categories.values())

    def create(self, data: CategoryCreate) -> CategoryResponse:
        category_id = uuid4()
        category = CategoryResponse(
            id=category_id,
            name=data.name,
            color=data.color,
            icon=data.icon,
        )
        self._categories[category_id] = category
        return category

    def update(
        self, category_id: UUID, data: CategoryUpdate
    ) -> CategoryResponse:
        if category_id not in self._categories:
            raise NotFoundError("카테고리를 찾을 수 없습니다")

        category = self._categories[category_id]
        updated = CategoryResponse(
            id=category.id,
            name=data.name if data.name is not None else category.name,
            color=data.color if data.color is not None else category.color,
            icon=data.icon if data.icon is not None else category.icon,
        )
        self._categories[category_id] = updated
        return updated

    def delete(self, category_id: UUID) -> None:
        if category_id not in self._categories:
            raise NotFoundError("카테고리를 찾을 수 없습니다")
        del self._categories[category_id]


class FakeEventService:
    """테스트용 Fake Event 서비스

    Usage:
        fake_service = FakeEventService()
        app.dependency_overrides[get_event_service] = lambda: fake_service
    """

    def __init__(self):
        self._events: dict[UUID, EventResponse] = {}
        self._registered_firebase_uids: set[str] = set()

    def register_firebase_uid(self, firebase_uid: str) -> None:
        """테스트용 Firebase UID 등록"""
        self._registered_firebase_uids.add(firebase_uid)

    def add_event(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        member_name: str = "테스트",
        member_color: str = "#FF0000",
        category_name: str | None = None,
        category_color: str | None = None,
        all_day: bool = False,
        description: str | None = None,
    ) -> EventResponse:
        """테스트용 이벤트 추가"""
        event_id = uuid4()
        now = datetime.now(timezone.utc)
        event = EventResponse(
            id=event_id,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            member=MemberInfo(name=member_name, color=member_color),
            category=CategoryInfo(name=category_name, color=category_color)
            if category_name
            else None,
            is_recurring=False,
            occurrence_date=None,
            created_at=now,
            updated_at=now,
        )
        self._events[event_id] = event
        return event

    def get_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[EventResponse]:
        result = []
        for event in self._events.values():
            event_date = event.start_time.date()
            if start_date <= event_date <= end_date:
                result.append(event)
        return result

    def create(
        self, data: EventCreate, creator_firebase_uid: str
    ) -> EventResponse:
        if creator_firebase_uid not in self._registered_firebase_uids:
            raise ForbiddenError("등록되지 않은 가족입니다")

        event_id = uuid4()
        now = datetime.now(timezone.utc)
        event = EventResponse(
            id=event_id,
            title=data.title,
            description=data.description,
            start_time=data.start_time,
            end_time=data.end_time,
            all_day=data.all_day,
            member=MemberInfo(name="테스트 유저", color="#000000"),
            category=None,
            is_recurring=data.recurrence_rule is not None,
            occurrence_date=None,
            created_at=now,
            updated_at=now,
        )
        self._events[event_id] = event
        return event

    def update(self, event_id: UUID, data: EventUpdate) -> EventResponse:
        if event_id not in self._events:
            raise NotFoundError("일정을 찾을 수 없습니다")

        event = self._events[event_id]
        update_dict = data.model_dump(exclude_unset=True)

        updated = EventResponse(
            id=event.id,
            title=update_dict.get("title", event.title),
            description=update_dict.get("description", event.description),
            start_time=update_dict.get("start_time", event.start_time),
            end_time=update_dict.get("end_time", event.end_time),
            all_day=update_dict.get("all_day", event.all_day),
            member=event.member,
            category=event.category,
            is_recurring=event.is_recurring,
            occurrence_date=event.occurrence_date,
            created_at=event.created_at,
            updated_at=datetime.now(timezone.utc),
        )
        self._events[event_id] = updated
        return updated

    def delete(self, event_id: UUID) -> None:
        if event_id not in self._events:
            raise NotFoundError("일정을 찾을 수 없습니다")
        del self._events[event_id]


@dataclass
class FakePendingEvent:
    """Fake PendingEvent 모델"""

    id: UUID
    event_data: list[dict]
    source_text: str | None
    source_image_hash: str | None
    created_by: UUID
    status: str
    confidence: float
    ai_message: str | None
    created_at: datetime
    expires_at: datetime


class FakePendingEventService:
    """테스트용 Fake PendingEvent 서비스

    Usage:
        fake_service = FakePendingEventService()
        app.dependency_overrides[get_pending_event_service] = lambda: fake_service
    """

    def __init__(self, event_service: FakeEventService | None = None):
        self._pending: dict[UUID, FakePendingEvent] = {}
        self._by_user: dict[str, list[UUID]] = {}
        self._member_by_uid: dict[str, UUID] = {}
        self._event_service = event_service

    def set_member_mapping(self, firebase_uid: str, member_id: UUID):
        """Firebase UID와 Member ID 매핑 설정"""
        self._member_by_uid[firebase_uid] = member_id

    def create(
        self,
        event_data: list[dict],
        user_uid: str,
        source_text: str | None = None,
        source_image_hash: str | None = None,
        ai_message: str | None = None,
        confidence: float = 1.0,
        expires_minutes: int | None = None,
    ) -> FakePendingEvent:
        pending_id = uuid4()
        member_id = self._member_by_uid.get(user_uid, uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=expires_minutes or 30)

        pending = FakePendingEvent(
            id=pending_id,
            event_data=event_data,
            source_text=source_text,
            source_image_hash=source_image_hash,
            created_by=member_id,
            status="pending",
            confidence=confidence,
            ai_message=ai_message,
            created_at=now,
            expires_at=expires_at,
        )
        self._pending[pending_id] = pending

        if user_uid not in self._by_user:
            self._by_user[user_uid] = []
        self._by_user[user_uid].append(pending_id)

        return pending

    def get_by_id(self, pending_id: UUID) -> FakePendingEvent | None:
        return self._pending.get(pending_id)

    def get_pending_by_user(self, user_uid: str) -> list[FakePendingEvent]:
        pending_ids = self._by_user.get(user_uid, [])
        return [
            self._pending[pid]
            for pid in pending_ids
            if pid in self._pending and self._pending[pid].status == "pending"
        ]

    def confirm(
        self,
        pending_id: UUID,
        user_uid: str,
        modifications: list[EventCreate] | None = None,
    ) -> list[Any]:
        pending = self._pending.get(pending_id)
        if not pending:
            raise ValueError("PendingEvent not found")
        if pending.status != "pending":
            raise ValueError(f"Invalid status: {pending.status}")

        pending.status = "confirmed"

        # Create events
        created_events = []
        events_to_create = (
            modifications
            if modifications
            else [
                EventCreate(
                    title=e.get("title", ""),
                    start_time=e.get("start_time"),
                    end_time=e.get("end_time"),
                    all_day=e.get("all_day", False),
                    description=e.get("description"),
                    recurrence_rule=e.get("recurrence"),
                )
                for e in pending.event_data
            ]
        )

        if self._event_service:
            for event_data in events_to_create:
                event = self._event_service.create(event_data, user_uid)
                created_events.append(event)
        else:
            # Return fake events with IDs
            for _ in events_to_create:

                @dataclass
                class FakeEvent:
                    id: UUID

                created_events.append(FakeEvent(id=uuid4()))

        return created_events

    def cancel(self, pending_id: UUID, user_uid: str) -> None:
        pending = self._pending.get(pending_id)
        if not pending:
            raise ValueError("PendingEvent not found")
        pending.status = "cancelled"

    def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        count = 0
        for pending in self._pending.values():
            if pending.status == "pending" and pending.expires_at < now:
                pending.status = "expired"
                count += 1
        return count
