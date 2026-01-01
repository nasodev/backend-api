"""캘린더 서비스 의존성 주입"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.external.database import get_db
from app.services.calendar.protocol import (
    MemberServiceProtocol,
    CategoryServiceProtocol,
    EventServiceProtocol,
)
from app.services.calendar.service import (
    MemberService,
    CategoryService,
    EventService,
)


def get_member_service(
    db: Session = Depends(get_db),
) -> MemberServiceProtocol:
    """
    Member 서비스 의존성 주입 포인트

    테스트에서 override 가능:
        app.dependency_overrides[get_member_service] = lambda: FakeMemberService()
    """
    return MemberService(db)


def get_category_service(
    db: Session = Depends(get_db),
) -> CategoryServiceProtocol:
    """
    Category 서비스 의존성 주입 포인트

    테스트에서 override 가능:
        app.dependency_overrides[get_category_service] = lambda: FakeCategoryService()
    """
    return CategoryService(db)


def get_event_service(
    db: Session = Depends(get_db),
) -> EventServiceProtocol:
    """
    Event 서비스 의존성 주입 포인트

    테스트에서 override 가능:
        app.dependency_overrides[get_event_service] = lambda: FakeEventService()
    """
    return EventService(db)
