"""PendingEvent 서비스 - AI 파싱 결과 임시 저장"""

import logging
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ForbiddenError
from app.models import FamilyMember, PendingEvent, PendingEventStatus, Event
from app.schemas.calendar import EventCreate

logger = logging.getLogger(__name__)


class PendingEventService:
    """PendingEvent 서비스 (PendingEventServiceProtocol 구현)"""

    DEFAULT_EXPIRES_MINUTES = 30

    def __init__(self, db: Session):
        self.db = db

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

    def create(
        self,
        event_data: list[dict],
        user_uid: str,
        source_text: str | None = None,
        source_image_hash: str | None = None,
        ai_message: str | None = None,
        confidence: float = 1.0,
        expires_minutes: int | None = None,
    ) -> PendingEvent:
        """PendingEvent 생성

        Args:
            event_data: AI가 파싱한 일정 데이터 (list of dict)
            user_uid: Firebase UID
            source_text: 원본 텍스트 입력
            source_image_hash: 이미지 해시 (중복 방지용)
            ai_message: AI 응답 메시지
            confidence: AI 신뢰도 (0.0-1.0)
            expires_minutes: 만료 시간 (분), 기본 30분

        Returns:
            생성된 PendingEvent
        """
        member = self._get_member_by_firebase_uid(user_uid)
        expires = expires_minutes or self.DEFAULT_EXPIRES_MINUTES

        pending = PendingEvent(
            event_data={"events": event_data},
            source_text=source_text,
            source_image_hash=source_image_hash,
            created_by=member.id,
            ai_message=ai_message,
            confidence=confidence,
            expires_at=datetime.utcnow() + timedelta(minutes=expires),
        )
        self.db.add(pending)
        self.db.commit()
        self.db.refresh(pending)

        logger.info(
            f"PendingEvent created: {pending.id}, "
            f"events={len(event_data)}, expires_at={pending.expires_at}"
        )
        return pending

    def get_by_id(self, pending_id: UUID) -> PendingEvent | None:
        """ID로 PendingEvent 조회"""
        return (
            self.db.query(PendingEvent)
            .filter(PendingEvent.id == pending_id)
            .first()
        )

    def get_pending_by_user(self, user_uid: str) -> list[PendingEvent]:
        """사용자의 대기 중인 PendingEvent 목록 조회"""
        member = self._get_member_by_firebase_uid(user_uid)

        return (
            self.db.query(PendingEvent)
            .filter(
                PendingEvent.created_by == member.id,
                PendingEvent.status == PendingEventStatus.PENDING.value,
                PendingEvent.expires_at > datetime.utcnow(),
            )
            .order_by(PendingEvent.created_at.desc())
            .all()
        )

    def confirm(
        self,
        pending_id: UUID,
        user_uid: str,
        modifications: list[EventCreate] | None = None,
    ) -> list[Event]:
        """PendingEvent 확인 → Event 생성

        Args:
            pending_id: PendingEvent ID
            user_uid: 요청한 사용자의 Firebase UID
            modifications: 사용자가 수정한 일정 데이터 (없으면 원본 사용)

        Returns:
            생성된 Event 목록

        Raises:
            NotFoundError: PendingEvent가 없거나 만료된 경우
            ForbiddenError: 권한이 없는 경우
        """
        member = self._get_member_by_firebase_uid(user_uid)
        pending = self.get_by_id(pending_id)

        if not pending:
            raise NotFoundError("대기 중인 일정을 찾을 수 없습니다")

        # 만료 체크
        if pending.expires_at < datetime.utcnow():
            pending.status = PendingEventStatus.EXPIRED.value
            self.db.commit()
            raise NotFoundError("일정이 만료되었습니다")

        # 상태 체크
        if pending.status != PendingEventStatus.PENDING.value:
            raise NotFoundError(f"이미 처리된 일정입니다 (상태: {pending.status})")

        # 권한 체크 (본인만 확인 가능)
        if pending.created_by != member.id:
            raise ForbiddenError("권한이 없습니다")

        # Event 생성
        created_events: list[Event] = []

        if modifications:
            # 사용자가 수정한 데이터 사용
            event_data_list = [m.model_dump() for m in modifications]
        else:
            # 원본 데이터 사용
            event_data_list = pending.event_data.get("events", [])

        for event_data in event_data_list:
            event = Event(
                title=event_data.get("title"),
                description=event_data.get("description"),
                start_time=self._parse_datetime(event_data.get("start_time")),
                end_time=self._parse_datetime(event_data.get("end_time")),
                all_day=event_data.get("all_day", False),
                category_id=event_data.get("category_id"),
                created_by=member.id,
                recurrence_rule=event_data.get("recurrence_rule"),
                recurrence_end=event_data.get("recurrence_end"),
            )
            self.db.add(event)
            created_events.append(event)

        # PendingEvent 상태 업데이트
        pending.status = PendingEventStatus.CONFIRMED.value
        self.db.commit()

        # 생성된 Event들 refresh
        for event in created_events:
            self.db.refresh(event)

        logger.info(
            f"PendingEvent confirmed: {pending_id}, created {len(created_events)} events"
        )
        return created_events

    def cancel(self, pending_id: UUID, user_uid: str) -> None:
        """PendingEvent 취소

        Args:
            pending_id: PendingEvent ID
            user_uid: 요청한 사용자의 Firebase UID

        Raises:
            NotFoundError: PendingEvent가 없는 경우
            ForbiddenError: 권한이 없는 경우
        """
        member = self._get_member_by_firebase_uid(user_uid)
        pending = self.get_by_id(pending_id)

        if not pending:
            raise NotFoundError("대기 중인 일정을 찾을 수 없습니다")

        # 권한 체크
        if pending.created_by != member.id:
            raise ForbiddenError("권한이 없습니다")

        # 이미 처리된 경우
        if pending.status != PendingEventStatus.PENDING.value:
            raise NotFoundError(f"이미 처리된 일정입니다 (상태: {pending.status})")

        pending.status = PendingEventStatus.CANCELLED.value
        self.db.commit()

        logger.info(f"PendingEvent cancelled: {pending_id}")

    def cleanup_expired(self) -> int:
        """만료된 PendingEvent 정리

        Returns:
            정리된 레코드 수
        """
        result = (
            self.db.query(PendingEvent)
            .filter(
                PendingEvent.status == PendingEventStatus.PENDING.value,
                PendingEvent.expires_at < datetime.utcnow(),
            )
            .update({"status": PendingEventStatus.EXPIRED.value})
        )
        self.db.commit()

        if result > 0:
            logger.info(f"Cleaned up {result} expired PendingEvents")
        return result

    @staticmethod
    def _parse_datetime(value) -> datetime | None:
        """datetime 문자열 또는 datetime 객체를 datetime으로 변환"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            # ISO 형식 파싱
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        return None
