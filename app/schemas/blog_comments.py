"""Explicit public DTOs and secret-aware inputs for comments."""
import re
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator


def clean_text(value: str, maximum: int) -> str:
    value = value.strip()
    if not 1 <= len(value) <= maximum:
        raise ValueError(f'Must contain 1–{maximum} characters')
    return value


class CommentInput(BaseModel):
    model_config = ConfigDict(extra='forbid', hide_input_in_errors=True)


class PasswordInput(CommentInput):
    password: SecretStr | None = None

    @field_validator('password')
    @classmethod
    def password_valid(cls, value):
        if value is not None:
            raw = value.get_secret_value()
            if not 8 <= len(raw) <= 128 or not raw.strip():
                raise ValueError('Password must contain 8–128 characters and not be blank')
        return value


class CommentUpdate(PasswordInput):
    content: str

    @field_validator('content')
    @classmethod
    def content_valid(cls, value):
        return clean_text(value, 5000)


class CommentCreate(CommentUpdate):
    author_type: Literal['google', 'guest']
    parent_id: UUID | None = None
    guest_name: str | None = None

    @field_validator('guest_name')
    @classmethod
    def name_valid(cls, value):
        return clean_text(value, 40) if value is not None else None

    @model_validator(mode='after')
    def guest_fields(self):
        if self.author_type == 'guest' and (self.guest_name is None or self.password is None):
            raise ValueError('Guest name and password are required')
        return self


class Comment(BaseModel):
    post_slug: str | None
    id: UUID
    thread_slug: str
    parent_id: UUID | None
    author_type: Literal['google', 'guest', 'github']
    author_name: str
    content: str
    created_at: datetime
    updated_at: datetime
    is_deleted: bool
    can_edit: bool
    can_delete: bool
    source_url: str | None


class CommentPage(BaseModel):
    items: list[Comment]
    next_cursor: str | None
    total: int


class GithubCommentImport(CommentInput):
    external_id: str = Field(min_length=1, max_length=200)
    thread_slug: str = Field(min_length=1, max_length=200, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    author_name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=5000)
    created_at: datetime
    source_url: str = Field(max_length=1000)
    parent_external_id: str | None = Field(default=None, min_length=1, max_length=200)

    @field_validator('created_at')
    @classmethod
    def timestamp_valid(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError('An original UTC-aware past timestamp is required')
        return value.astimezone(timezone.utc)

    @field_validator('source_url')
    @classmethod
    def github_discussion(cls, value):
        url = urlsplit(value)
        if (url.scheme != 'https' or url.netloc != 'github.com' or url.query
                or not re.fullmatch(r'/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/discussions/[1-9][0-9]*/?', url.path)
                or (url.fragment and not re.fullmatch(r'discussioncomment-[0-9]+', url.fragment))):
            raise ValueError('A GitHub discussion or discussion-comment URL is required')
        return value


class GithubImportRequest(CommentInput):
    comments: list[GithubCommentImport] = Field(min_length=1, max_length=100)


class GithubImportResult(BaseModel):
    imported: int
    skipped: int
