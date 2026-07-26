"""블로그 서비스 Fake 구현"""

import uuid
from datetime import datetime
from types import SimpleNamespace

from fastapi import HTTPException

from app.schemas.blog import BlogPostCreate, BlogPostUpdate
from app.services.blog.content import process_content


class FakeBlogService:
    def __init__(self):
        self.posts: dict[str, SimpleNamespace] = {}

    def add_post(self, slug, title="제목", is_published=True, tags=None,
                 content_html="<p>본문</p>", description="설명"):
        """테스트 헬퍼 — process_content를 거쳐 실제 서비스와 동일한 toc 생성"""
        processed = process_content(content_html)
        post = SimpleNamespace(
            id=uuid.uuid4(),
            slug=slug,
            title=title,
            description=description,
            author="fundev",
            content_html=processed.content_html,
            cover_image_url=None,
            tags=tags or [],
            toc=processed.toc,
            reading_time_minutes=processed.reading_time_minutes,
            view_count=0,
            is_published=is_published,
            published_at=datetime(2026, 1, 1),
            updated_at=datetime(2026, 1, 1),
        )
        self.posts[slug] = post
        return post

    def list_published(self, tag=None, page=1, size=100):
        posts = [p for p in self.posts.values() if p.is_published]
        if tag:
            posts = [p for p in posts if tag in p.tags]
        posts.sort(key=lambda p: p.published_at, reverse=True)
        return posts[(page - 1) * size : page * size]

    def list_all(self):
        return sorted(self.posts.values(), key=lambda p: p.published_at, reverse=True)

    def get_published(self, slug):
        post = self.posts.get(slug)
        if not post or not post.is_published:
            raise HTTPException(404, detail="Post not found")
        return post

    def get_any(self, slug):
        post = self.posts.get(slug)
        if not post:
            raise HTTPException(404, detail="Post not found")
        return post

    def create(self, data: BlogPostCreate):
        if data.slug in self.posts:
            raise HTTPException(409, detail="Slug already exists")
        post = self.add_post(
            data.slug, title=data.title, is_published=data.is_published,
            tags=data.tags, content_html=data.content_html, description=data.description,
        )
        if data.published_at:
            post.published_at = data.published_at
        post.author = data.author
        post.cover_image_url = data.cover_image_url
        return post

    def update(self, slug, data: BlogPostUpdate):
        post = self.get_any(slug)
        fields = data.model_dump(exclude_unset=True)
        if "content_html" in fields:
            processed = process_content(fields.pop("content_html"))
            post.content_html = processed.content_html
            post.toc = processed.toc
            post.reading_time_minutes = processed.reading_time_minutes
        for key, value in fields.items():
            setattr(post, key, value)
        post.updated_at = datetime.utcnow()
        return post

    def delete(self, slug):
        self.get_any(slug)
        del self.posts[slug]

    def increment_view(self, slug):
        post = self.get_any(slug)
        post.view_count += 1
        return post.view_count
