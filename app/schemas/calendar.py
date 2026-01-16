"""캘린더 API 스키마"""

import re
from datetime import datetime, date
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# ============ Validators ============

def validate_hex_color(v: str) -> str:
    """#RRGGBB 형식의 유효한 hex 색상인지 검증"""
    if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
        raise ValueError('Color must be a valid hex color in #RRGGBB format (e.g., #FF5733)')
    return v.upper()  # 일관성을 위해 대문자로 정규화


# ============ Recurrence ============

class RecurrenceFrequency(str, Enum):
    """반복 주기"""
    DAILY = "DAILY"      # 매일
    WEEKLY = "WEEKLY"    # 매주
    MONTHLY = "MONTHLY"  # 매월
    YEARLY = "YEARLY"    # 매년


class Weekday(str, Enum):
    """요일"""
    MO = "MO"  # 월요일
    TU = "TU"  # 화요일
    WE = "WE"  # 수요일
    TH = "TH"  # 목요일
    FR = "FR"  # 금요일
    SA = "SA"  # 토요일
    SU = "SU"  # 일요일


class RecurrencePattern(BaseModel):
    """반복 패턴 (RRULE 생성 헬퍼)

    Examples:
        매일: {"frequency": "DAILY"}
        매주: {"frequency": "WEEKLY"}
        매주 월,수,금: {"frequency": "WEEKLY", "weekdays": ["MO", "WE", "FR"]}
        격주: {"frequency": "WEEKLY", "interval": 2}
        매월: {"frequency": "MONTHLY"}
        매년: {"frequency": "YEARLY"}
    """
    frequency: RecurrenceFrequency
    interval: int = 1  # 반복 간격 (1=매번, 2=격주/격월 등)
    weekdays: Optional[list[Weekday]] = None  # WEEKLY일 때 요일 지정
    count: Optional[int] = None  # 반복 횟수 (until과 함께 사용 불가)
    until: Optional[date] = None  # 반복 종료일 (count와 함께 사용 불가)

    def to_rrule(self) -> str:
        """RRULE 문자열로 변환"""
        parts = [f"FREQ={self.frequency.value}", f"INTERVAL={self.interval}"]

        if self.weekdays and self.frequency == RecurrenceFrequency.WEEKLY:
            days = ",".join(day.value for day in self.weekdays)
            parts.append(f"BYDAY={days}")

        if self.until:
            until_dt = datetime.combine(self.until, datetime.max.time())
            parts.append(f"UNTIL={until_dt.strftime('%Y%m%dT%H%M%SZ')}")
        elif self.count:
            parts.append(f"COUNT={self.count}")

        return ";".join(parts)


# ============ FamilyMember ============

class FamilyMemberBase(BaseModel):
    display_name: str
    color: str

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        return validate_hex_color(v)


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    display_name: Optional[str] = None
    color: Optional[str] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_hex_color(v)
        return v


class FamilyMemberResponse(FamilyMemberBase):
    id: UUID
    email: str
    is_registered: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============ Category ============

class CategoryBase(BaseModel):
    name: str
    color: str
    icon: Optional[str] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        return validate_hex_color(v)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_hex_color(v)
        return v


class CategoryResponse(CategoryBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


# ============ Event ============

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    all_day: bool = False
    category_id: Optional[UUID] = None
    recurrence_rule: Optional[str] = None
    recurrence_pattern: Optional[RecurrencePattern] = None  # RRULE 대신 패턴으로 지정
    recurrence_end: Optional[date] = None

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        start_time = info.data.get('start_time')
        if start_time and v < start_time:
            raise ValueError('end_time must be after start_time')
        return v


class EventCreate(EventBase):
    """일정 생성 요청

    반복 일정 지정 방법:
    1. recurrence_rule: RRULE 문자열 직접 지정
    2. recurrence_pattern: 패턴 객체로 지정 (권장)

    둘 다 지정 시 recurrence_pattern이 우선 적용됩니다.
    """

    def get_rrule(self) -> Optional[str]:
        """RRULE 문자열 반환 (pattern 우선)"""
        if self.recurrence_pattern:
            return self.recurrence_pattern.to_rrule()
        return self.recurrence_rule


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    category_id: Optional[UUID] = None
    recurrence_rule: Optional[str] = None
    recurrence_pattern: Optional[RecurrencePattern] = None
    recurrence_end: Optional[date] = None

    def get_rrule(self) -> Optional[str]:
        """RRULE 문자열 반환 (pattern 우선)"""
        if self.recurrence_pattern:
            return self.recurrence_pattern.to_rrule()
        return self.recurrence_rule


class MemberInfo(BaseModel):
    name: str
    color: str


class CategoryInfo(BaseModel):
    name: str
    color: str


class EventResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    all_day: bool
    member: MemberInfo
    category: Optional[CategoryInfo]
    is_recurring: bool
    occurrence_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EventListResponse(BaseModel):
    events: list[EventResponse]


# ============ Auth ============

class AuthVerifyResponse(BaseModel):
    valid: bool
    member: FamilyMemberResponse
