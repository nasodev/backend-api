"""캘린더 API 스키마"""

from datetime import datetime, date
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


# ============ FamilyMember ============

class FamilyMemberBase(BaseModel):
    display_name: str
    color: str

    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not v.startswith('#') or len(v) != 7:
            raise ValueError('Color must be in #RRGGBB format')
        return v


class FamilyMemberCreate(FamilyMemberBase):
    pass


class FamilyMemberUpdate(BaseModel):
    display_name: Optional[str] = None
    color: Optional[str] = None


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


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


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
    recurrence_start: Optional[date] = None
    recurrence_end: Optional[date] = None

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v: datetime, info) -> datetime:
        start_time = info.data.get('start_time')
        if start_time and v < start_time:
            raise ValueError('end_time must be after start_time')
        return v


class EventCreate(EventBase):
    pass


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    all_day: Optional[bool] = None
    category_id: Optional[UUID] = None
    recurrence_rule: Optional[str] = None
    recurrence_start: Optional[date] = None
    recurrence_end: Optional[date] = None


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
