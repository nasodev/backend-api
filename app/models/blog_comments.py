"""Comments belong to translation-independent threads, never to one post row."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.external.database import Base
from app.models.blog import _utcnow


class BlogComment(Base):
    __tablename__ = 'blog_comments'
    __table_args__ = (
        CheckConstraint("author_type IN ('google', 'guest', 'github')", name='ck_blog_comments_author_type'),
        Index('ix_blog_comments_thread_created_id', 'thread_slug', 'created_at', 'id'),
        Index('ix_blog_comments_parent', 'parent_id'),
        Index('ix_blog_comments_author_created', 'author_uid', 'created_at'),
        Index('ix_blog_comments_rate_created', 'creation_rate_key', 'created_at'),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_slug: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('blog_comments.id'))
    author_type: Mapped[str] = mapped_column(String(10), nullable=False)
    author_uid: Mapped[str | None] = mapped_column(String(128))
    password_hash: Mapped[str | None] = mapped_column(String(256))
    creation_rate_key: Mapped[str | None] = mapped_column(String(64))
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    external_id: Mapped[str | None] = mapped_column(String(200), unique=True)
    source_url: Mapped[str | None] = mapped_column(String(1000))


class BlogCommentPasswordAttempt(Base):
    __tablename__ = 'blog_comment_password_attempts'
    __table_args__ = (Index('ix_blog_comment_attempt_actor_created', 'actor_key', 'created_at'),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
