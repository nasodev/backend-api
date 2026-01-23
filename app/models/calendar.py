"""캘린더 관련 데이터베이스 모델"""

import uuid
from datetime import datetime, date
from enum import Enum
from typing import Optional

from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime, Date, Index, Float
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.external.database import Base


class PendingEventStatus(str, Enum):
    """PendingEvent 상태"""
    PENDING = "pending"      # 대기 중
    CONFIRMED = "confirmed"  # 승인됨 → Event 생성됨
    EXPIRED = "expired"      # 만료됨
    CANCELLED = "cancelled"  # 취소됨


class FamilyMember(Base):
    """가족 구성원"""
    __tablename__ = "family_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    firebase_uid: Mapped[Optional[str]] = mapped_column(
        String(128), unique=True, nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)  # #RRGGBB
    is_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # Relationships
    events: Mapped[list["Event"]] = relationship(back_populates="creator")


class Category(Base):
    """일정 카테고리"""
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)  # #RRGGBB
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Relationships
    events: Mapped[list["Event"]] = relationship(back_populates="category")


class Event(Base):
    """일정"""
    __tablename__ = "events"
    __table_args__ = (
        # 날짜 범위 쿼리 최적화를 위한 인덱스
        Index("ix_events_start_time", "start_time"),
        Index("ix_events_recurrence_end", "recurrence_end"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    all_day: Mapped[bool] = mapped_column(Boolean, default=False)

    # Foreign Keys
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False
    )

    # Recurrence
    recurrence_rule: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True
    )  # RRULE format
    recurrence_start: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )
    recurrence_end: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    category: Mapped[Optional["Category"]] = relationship(back_populates="events")
    creator: Mapped["FamilyMember"] = relationship(back_populates="events")
    exceptions: Mapped[list["RecurrenceException"]] = relationship(
        back_populates="event", cascade="all, delete-orphan"
    )


class RecurrenceException(Base):
    """반복 일정 예외"""
    __tablename__ = "recurrence_exceptions"
    __table_args__ = (
        # event_id로 조회 최적화 (PostgreSQL은 FK에 자동 인덱스 안 만듦)
        Index("ix_recurrence_exceptions_event_id", "event_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("events.id"), nullable=False
    )
    original_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    modified_event: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Relationships
    event: Mapped["Event"] = relationship(back_populates="exceptions")


class PendingEvent(Base):
    """AI 파싱 후 확인 대기 중인 일정"""
    __tablename__ = "pending_events"
    __table_args__ = (
        Index("ix_pending_events_created_by", "created_by"),
        Index("ix_pending_events_status", "status"),
        Index("ix_pending_events_expires_at", "expires_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 파싱된 일정 데이터 (JSON 배열)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # 원본 입력
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_image_hash: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True
    )  # 이미지 해시 (중복 방지용)

    # 메타데이터
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("family_members.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PendingEventStatus.PENDING.value
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    ai_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # TTL 관리
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Relationships
    created_by_member: Mapped["FamilyMember"] = relationship()
