"""캘린더 관리자 라우터"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.external.database import get_db
from app.dependencies.auth import get_current_user
from app.dependencies.entities import FirebaseUser
from app.models.calendar import RecurrenceException, Event, Category, FamilyMember

router = APIRouter(prefix="/admin", tags=["calendar-admin"])


@router.delete("/reset", status_code=200)
def reset_calendar_data(
    user: FirebaseUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """모든 캘린더 데이터를 초기화합니다.

    삭제 순서 (FK 관계):
    1. RecurrenceException
    2. Event
    3. Category
    4. FamilyMember
    """

    # 삭제 순서: FK 의존성 순서대로
    deleted_exceptions = db.query(RecurrenceException).delete()
    deleted_events = db.query(Event).delete()
    deleted_categories = db.query(Category).delete()
    deleted_members = db.query(FamilyMember).delete()

    db.commit()

    return {
        "message": "Calendar data reset successfully",
        "deleted": {
            "recurrence_exceptions": deleted_exceptions,
            "events": deleted_events,
            "categories": deleted_categories,
            "family_members": deleted_members,
        },
    }
