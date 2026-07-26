"""블로그 API 스키마"""

import re
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

MAX_CONTENT_LENGTH = 2_000_000  # 2MB 상당
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_content_size(v: str) -> str:
    if len(v) > MAX_CONTENT_LENGTH:
        raise ValueError(f"content_html exceeds {MAX_CONTENT_LENGTH} characters")
    return v


class BlogPostCreate(BaseModel):
    slug: str
    title: str
    description: str
    content_html: str
    author: str = "fundev"
    cover_image_url: Optional[str] = None
    tags: list[str] = []
    is_published: bool = True
    published_at: Optional[datetime] = None  # None이면 서버가 현재 시각

    @field_validator("slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not SLUG_PATTERN.match(v):
            raise ValueError("slug must be kebab-case (a-z, 0-9, hyphen)")
        return v

    @field_validator("content_html")
    @classmethod
    def content_size(cls, v: str) -> str:
        return validate_content_size(v)


class BlogPostUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content_html: Optional[str] = None
    author: Optional[str] = None
    cover_image_url: Optional[str] = None
    tags: Optional[list[str]] = None
    is_published: Optional[bool] = None
    published_at: Optional[datetime] = None

    @field_validator("title", "description", "content_html", "author", "tags", "is_published", "published_at")
    @classmethod
    def reject_explicit_null(cls, v, info):
        if v is None:
            raise ValueError(f"{info.field_name} cannot be explicitly set to null; omit the field for partial updates")
        return v

    @field_validator("content_html")
    @classmethod
    def content_size(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return validate_content_size(v)


class BlogPostSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    title: str
    description: str
    author: str
    cover_image_url: Optional[str]
    tags: list[str]
    reading_time_minutes: int
    view_count: int
    published_at: datetime
    updated_at: datetime


class BlogPostDetail(BlogPostSummary):
    content_html: str
    toc: list[dict]
    is_published: bool


class ViewCountResponse(BaseModel):
    view_count: int


class ImageUploadResponse(BaseModel):
    url: str
    filename: str
