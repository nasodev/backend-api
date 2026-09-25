"""Exercise view aggregation through real SQLAlchemy queries and persisted rows."""

from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.models.blog import BlogPost
from app.services.blog.service import BlogService


@compiles(JSONB, "sqlite")
def sqlite_jsonb(_type, _compiler, **_kwargs):
    """Only adapt JSONB DDL; view tests execute the real ORM aggregation SQL."""
    return "JSON"


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    BlogPost.__table__.create(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_post(db, slug, views=0, published=True, day=1):
    post = BlogPost(
        slug=slug, title=slug, description="A post", content_html="<p>Text</p>",
        author="fundev", tags=[], toc=[], view_count=views,
        is_published=published, published_at=datetime(2026, 9, day, tzinfo=timezone.utc),
    )
    db.add(post)
    db.flush()
    return post


def test_both_details_have_shared_total_without_changing_stored_counts(db):
    add_post(db, "guide", 100)
    add_post(db, "en-guide", 20)
    add_post(db, "guide-extra", 500)
    add_post(db, "en-guide-extra", 600)
    db.commit()
    service = BlogService(db)

    korean = service.get_published("guide")
    english = service.get_published("en-guide")
    assert (korean.view_count, korean.total_view_count) == (100, 120)
    assert (english.view_count, english.total_view_count) == (20, 120)
    db.commit()
    assert dict(db.execute(select(BlogPost.slug, BlogPost.view_count)).all()) == {
        "guide": 100, "en-guide": 20, "guide-extra": 500, "en-guide-extra": 600,
    }
    assert "total_view_count" not in BlogPost.__table__.columns


@pytest.mark.parametrize("slug,counterpart", [("guide", "en-guide"), ("en-guide", "guide")])
@pytest.mark.parametrize("counterpart_state", ["missing", "draft"])
def test_missing_or_unpublished_counterpart_does_not_contribute(db, slug, counterpart, counterpart_state):
    add_post(db, slug, 100)
    if counterpart_state == "draft":
        add_post(db, counterpart, 20, published=False)
    db.commit()
    assert BlogService(db).get_published(slug).total_view_count == 100


def test_list_total_includes_counterpart_outside_requested_page(db):
    add_post(db, "guide", 100, day=20)
    add_post(db, "en-guide", 20, day=1)
    db.commit()

    page = BlogService(db).list_published(page=1, size=1)
    assert len(page) == 1
    assert page[0].slug == "guide"
    assert page[0].total_view_count == 120


@pytest.mark.parametrize("slug,raw", [("guide", 101), ("en-guide", 21)])
def test_increment_updates_only_visited_language_and_returns_total(db, slug, raw):
    add_post(db, "guide", 100)
    add_post(db, "en-guide", 20)
    db.commit()

    counts = BlogService(db).increment_view(slug)
    assert counts.model_dump() == {"view_count": raw, "total_view_count": 121}
    stored = dict(db.execute(select(BlogPost.slug, BlogPost.view_count)).all())
    assert stored == ({"guide": 101, "en-guide": 20} if slug == "guide" else {"guide": 100, "en-guide": 21})
    assert BlogService(db).get_published("guide").total_view_count == 121
    assert BlogService(db).get_published("en-guide").total_view_count == 121


def test_zero_views_and_newly_published_translation_are_reflected(db):
    add_post(db, "guide")
    translation = add_post(db, "en-guide", 20, published=False)
    db.commit()
    service = BlogService(db)
    assert service.get_published("guide").total_view_count == 0

    translation.is_published = True
    db.commit()
    assert service.get_published("guide").total_view_count == 20
    service.delete("en-guide")
    assert service.get_published("guide").total_view_count == 0


@pytest.mark.parametrize("slug", ["missing", "draft"])
def test_missing_or_unpublished_visits_remain_404_without_increment(db, slug):
    add_post(db, "draft", 10, published=False)
    db.commit()
    with pytest.raises(HTTPException) as exc:
        BlogService(db).increment_view(slug)
    assert exc.value.status_code == 404
    assert db.scalar(select(BlogPost.view_count).where(BlogPost.slug == "draft")) == 10
