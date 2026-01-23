"""캘린더 서비스 인터페이스 정의"""

from typing import Protocol
from uuid import UUID
from datetime import date

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
)


class MemberServiceProtocol(Protocol):
    """가족 구성원 서비스 인터페이스 (TDD용 추상화)"""

    def get_all(self) -> list[FamilyMemberResponse]:
        """모든 구성원 조회"""
        ...

    def create(self, data: FamilyMemberCreate) -> FamilyMemberResponse:
        """구성원 생성"""
        ...

    def update(
        self, member_id: UUID, data: FamilyMemberUpdate
    ) -> FamilyMemberResponse:
        """구성원 수정"""
        ...

    def delete(self, member_id: UUID) -> None:
        """구성원 삭제"""
        ...

    def get_by_firebase_uid(self, firebase_uid: str) -> FamilyMemberResponse | None:
        """Firebase UID로 구성원 조회"""
        ...

    def verify_and_link(
        self, email: str, firebase_uid: str
    ) -> FamilyMemberResponse:
        """Firebase UID로 구성원 찾거나 자동 생성

        기존 구성원이면 반환, 없으면 자동 생성합니다.

        Returns:
            FamilyMemberResponse (항상 반환)
        """
        ...


class CategoryServiceProtocol(Protocol):
    """카테고리 서비스 인터페이스 (TDD용 추상화)"""

    def get_all(self) -> list[CategoryResponse]:
        """모든 카테고리 조회"""
        ...

    def create(self, data: CategoryCreate) -> CategoryResponse:
        """카테고리 생성"""
        ...

    def update(
        self, category_id: UUID, data: CategoryUpdate
    ) -> CategoryResponse:
        """카테고리 수정"""
        ...

    def delete(self, category_id: UUID) -> None:
        """카테고리 삭제"""
        ...


class EventServiceProtocol(Protocol):
    """일정 서비스 인터페이스 (TDD용 추상화)"""

    def get_by_date_range(
        self, start_date: date, end_date: date
    ) -> list[EventResponse]:
        """기간 내 일정 조회"""
        ...

    def create(
        self, data: EventCreate, creator_firebase_uid: str
    ) -> EventResponse:
        """일정 생성"""
        ...

    def update(self, event_id: UUID, data: EventUpdate) -> EventResponse:
        """일정 수정"""
        ...

    def delete(self, event_id: UUID) -> None:
        """일정 삭제"""
        ...


class PendingEventServiceProtocol(Protocol):
    """PendingEvent 서비스 인터페이스 (TDD용 추상화)"""

    def create(
        self,
        event_data: list[dict],
        user_uid: str,
        source_text: str | None = None,
        source_image_hash: str | None = None,
        ai_message: str | None = None,
        confidence: float = 1.0,
        expires_minutes: int | None = None,
    ):
        """PendingEvent 생성"""
        ...

    def get_by_id(self, pending_id: UUID):
        """ID로 PendingEvent 조회"""
        ...

    def get_pending_by_user(self, user_uid: str) -> list:
        """사용자의 대기 중인 PendingEvent 목록 조회"""
        ...

    def confirm(
        self,
        pending_id: UUID,
        user_uid: str,
        modifications: list[EventCreate] | None = None,
    ) -> list:
        """PendingEvent 확인 → Event 생성"""
        ...

    def cancel(self, pending_id: UUID, user_uid: str) -> None:
        """PendingEvent 취소"""
        ...

    def cleanup_expired(self) -> int:
        """만료된 PendingEvent 정리"""
        ...
