"""블로그 서비스 구현"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.blog import BlogPost
from app.schemas.blog import BlogPostCreate, BlogPostUpdate
from app.services.blog.content import process_content


class BlogService:
    def __init__(self, db: Session):
        self.db = db

    def list_published(self, tag: str | None = None, page: int = 1, size: int = 100) -> list[BlogPost]:
        query = self.db.query(BlogPost).filter(BlogPost.is_published.is_(True))
        if tag:
            query = query.filter(BlogPost.tags.contains([tag]))
        return (
            query.order_by(BlogPost.published_at.desc())
            .offset((page - 1) * size)
            .limit(size)
            .all()
        )

    def list_all(self) -> list[BlogPost]:
        return self.db.query(BlogPost).order_by(BlogPost.published_at.desc()).all()

    def get_published(self, slug: str) -> BlogPost:
        post = (
            self.db.query(BlogPost)
            .filter(BlogPost.slug == slug, BlogPost.is_published.is_(True))
            .first()
        )
        if not post:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    def get_any(self, slug: str) -> BlogPost:
        post = self.db.query(BlogPost).filter(BlogPost.slug == slug).first()
        if not post:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
        return post

    def create(self, data: BlogPostCreate) -> BlogPost:
        exists = self.db.query(BlogPost).filter(BlogPost.slug == data.slug).first()
        if exists:
            raise HTTPException(status.HTTP_409_CONFLICT, detail="Slug already exists")

        processed = process_content(data.content_html)
        post = BlogPost(
            slug=data.slug,
            title=data.title,
            description=data.description,
            author=data.author,
            content_html=processed.content_html,
            cover_image_url=data.cover_image_url,
            tags=data.tags,
            toc=processed.toc,
            reading_time_minutes=processed.reading_time_minutes,
            is_published=data.is_published,
            published_at=data.published_at or datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self.db.add(post)
        self.db.commit()
        self.db.refresh(post)
        return post

    def update(self, slug: str, data: BlogPostUpdate) -> BlogPost:
        post = self.get_any(slug)
        fields = data.model_dump(exclude_unset=True)

        if "content_html" in fields:
            processed = process_content(fields.pop("content_html"))
            post.content_html = processed.content_html
            post.toc = processed.toc
            post.reading_time_minutes = processed.reading_time_minutes

        for key, value in fields.items():
            setattr(post, key, value)

        post.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(post)
        return post

    def delete(self, slug: str) -> None:
        post = self.get_any(slug)
        self.db.delete(post)
        self.db.commit()

    def increment_view(self, slug: str) -> int:
        result = self.db.execute(
            update(BlogPost)
            .where(BlogPost.slug == slug, BlogPost.is_published.is_(True))
            .values(view_count=BlogPost.view_count + 1)
            .returning(BlogPost.view_count)
        )
        row = result.first()
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Post not found")
        self.db.commit()
        return row[0]
