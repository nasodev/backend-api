"""블로그 데이터베이스 모델"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import String, Boolean, Text, Integer, DateTime, Index, case, func, select
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, column_property, mapped_column

from app.external.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BlogPost(Base):
    """블로그 글 (HTML 본문 + 메타데이터 + 조회수)"""
    __tablename__ = "blog_posts"
    __table_args__ = (
        Index("ix_blog_posts_published_at", "published_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False, default="fundev")
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    tags: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    toc: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reading_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


# A read-only SELECT expression, not a stored column. Keep the existing per-language
# counters and compute the total independently of the outer query's page/tag filter.
_view_posts = BlogPost.__table__.alias("view_posts")
_counterpart_slug = case(
    (BlogPost.slug.like("en-%"), func.substr(BlogPost.slug, 4)),
    else_="en-" + BlogPost.slug,
)
BlogPost.total_view_count = column_property(
    select(func.coalesce(func.sum(_view_posts.c.view_count), 0))
    .where(
        _view_posts.c.is_published.is_(True),
        _view_posts.c.slug.in_([BlogPost.__table__.c.slug, _counterpart_slug]),
    )
    .correlate_except(_view_posts)
    .scalar_subquery()
)
