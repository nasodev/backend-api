"""캘린더 서비스 모듈"""

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
from app.exceptions import (
    NotFoundError,
    DuplicateError,
    ForbiddenError,
)
from app.services.calendar.dependencies import (
    get_member_service,
    get_category_service,
    get_event_service,
)
from app.services.calendar.recurrence import (
    RecurrenceFrequency,
    Weekday,
    build_rrule,
    get_occurrences,
)

__all__ = [
    # Protocols
    "MemberServiceProtocol",
    "CategoryServiceProtocol",
    "EventServiceProtocol",
    # Services
    "MemberService",
    "CategoryService",
    "EventService",
    # Errors
    "NotFoundError",
    "DuplicateError",
    "ForbiddenError",
    # Dependencies
    "get_member_service",
    "get_category_service",
    "get_event_service",
    # Recurrence
    "RecurrenceFrequency",
    "Weekday",
    "build_rrule",
    "get_occurrences",
]
