"""Native comment persistence, permissions, database-backed limits and imports.

Each mutation owns its transaction. In particular password attempts commit before
verification so a rejected request cannot roll back the brute-force budget.
"""
import hashlib
import math
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import and_, delete, func, or_, select, text

from app.config import get_settings
from app.models.blog import BlogPost
from app.models.blog_comments import BlogComment, BlogCommentPasswordAttempt
from app.schemas.blog_comments import Comment, CommentPage, GithubImportResult
from app.services.blog.comment_paging import decode_cursor, encode_cursor, utc
from app.services.blog.comment_security import guest_key, hash_password, verify_password


def canonical_thread(slug):
    return slug[3:] if slug.startswith('en-') else slug


def google_user(user):
    return bool(user and user.token_data.get('firebase', {}).get('sign_in_provider') == 'google.com')


class CommentService:
    def __init__(self, db, settings=None):
        self.db = db
        self.settings = settings or get_settings()

    def _lock(self, key):
        # A stable signed 64-bit value, unlike process-randomized Python hash().
        if self.db.get_bind().dialect.name != 'sqlite':
            lock_id = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], 'big', signed=True)
            self.db.execute(text('SELECT pg_advisory_xact_lock(:key)'), {'key': lock_id})

    def _thread(self, slug):
        exists = self.db.scalar(select(BlogPost.id).where(BlogPost.slug == slug, BlogPost.is_published.is_(True)))
        if exists is None:
            raise HTTPException(404, 'Published post not found')
        return canonical_thread(slug)

    def _admin(self, user):
        return bool(user and user.uid in self.settings.blog_admin_uids)

    def _owner(self, row, user):
        return row.author_type == 'google' and google_user(user) and row.author_uid == user.uid

    def _public(self, row, user, post_slug=None):
        active = row.deleted_at is None
        return Comment(
            id=row.id, thread_slug=row.thread_slug, parent_id=row.parent_id, post_slug=post_slug,
            author_type=row.author_type, author_name=row.author_name if active else '',
            content=row.content if active else '', created_at=utc(row.created_at),
            updated_at=utc(row.updated_at), is_deleted=not active,
            can_edit=active and self._owner(row, user),
            can_delete=active and (self._owner(row, user) or self._admin(user)),
            source_url=row.source_url,
        )

    def list(self, slug=None, user=None, limit=20, cursor=None):
        if not 1 <= limit <= 50:
            raise HTTPException(422, 'Limit must be between 1 and 50')
        thread = self._thread(slug) if slug is not None else None
        scope = f'thread:{thread}' if thread is not None else 'admin'
        query = select(BlogComment)
        count = select(func.count()).select_from(BlogComment).where(BlogComment.deleted_at.is_(None))
        if thread is not None:
            query = query.where(BlogComment.thread_slug == thread)
            count = count.where(BlogComment.thread_slug == thread)
        if cursor is not None:
            stamp, identifier = decode_cursor(cursor, scope)
            if thread is not None:
                query = query.where(or_(BlogComment.created_at > stamp, and_(BlogComment.created_at == stamp, BlogComment.id > identifier)))
            else:
                query = query.where(or_(BlogComment.created_at < stamp, and_(BlogComment.created_at == stamp, BlogComment.id < identifier)))
        order = (BlogComment.created_at, BlogComment.id) if thread is not None else (BlogComment.created_at.desc(), BlogComment.id.desc())
        rows = list(self.db.scalars(query.order_by(*order).limit(limit + 1)))
        public_slugs = {}
        if thread is None and rows:
            threads = {row.thread_slug for row in rows[:limit]}
            candidates = threads | {'en-' + name for name in threads}
            published = set(self.db.scalars(select(BlogPost.slug).where(
                BlogPost.slug.in_(candidates), BlogPost.is_published.is_(True))))
            public_slugs = {name: name if name in published else ('en-' + name if 'en-' + name in published else None)
                            for name in threads}
        return CommentPage(items=[self._public(row, user, slug if thread is not None else public_slugs[row.thread_slug]) for row in rows[:limit]],
                           next_cursor=encode_cursor(rows[limit - 1], scope) if len(rows) > limit else None,
                           total=self.db.scalar(count))

    def _row(self, identifier, thread=None, lock=False):
        query = select(BlogComment).where(BlogComment.id == identifier)
        if thread is not None:
            query = query.where(BlogComment.thread_slug == thread)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.db.scalar(query)
        if row is None:
            raise HTTPException(404, 'Comment not found')
        return row

    def _creation_budget(self, key, now):
        self._lock('comment-create:' + key)
        oldest, latest, count = self.db.execute(select(func.min(BlogComment.created_at), func.max(BlogComment.created_at), func.count()).where(
            BlogComment.creation_rate_key == key, BlogComment.created_at > now - timedelta(days=1))).one()
        wait = 0
        if latest:
            wait = max(wait, 15 - (now - utc(latest)).total_seconds())
        if count >= 100:
            wait = max(wait, 86400 - (now - utc(oldest)).total_seconds())
        if wait > 0:
            raise HTTPException(429, 'Comment creation limit reached', headers={'Retry-After': str(math.ceil(wait))})

    def create(self, slug, data, user=None, address=''):
        try:
            thread = self._thread(slug)
            if data.author_type == 'google':
                if user is None:
                    raise HTTPException(401, 'Google authentication required')
                if not google_user(user):
                    raise HTTPException(403, 'Google authentication required')
                key = hashlib.sha256(('google:' + user.uid).encode()).hexdigest()
            else:
                key = guest_key(address, self.settings.blog_comment_hash_secret)
            now = datetime.now(timezone.utc)
            self._creation_budget(key, now)
            if data.parent_id:
                parent = self.db.scalar(select(BlogComment).where(BlogComment.id == data.parent_id).with_for_update())
                if not parent or parent.thread_slug != thread or parent.parent_id or parent.deleted_at:
                    raise HTTPException(400, 'Invalid reply parent')
            # All cheap auth/rate/parent checks precede the deliberately expensive KDF.
            row = BlogComment(thread_slug=thread, parent_id=data.parent_id, author_type=data.author_type,
                              author_uid=user.uid if data.author_type == 'google' else None,
                              author_name=(user.name or 'Google user')[:200] if data.author_type == 'google' else data.guest_name,
                              password_hash=hash_password(data.password.get_secret_value()) if data.author_type == 'guest' else None,
                              creation_rate_key=key, content=data.content, created_at=now, updated_at=now)
            self.db.add(row)
            self.db.commit()
            return self._public(row, user, slug)
        except Exception:
            self.db.rollback()
            raise

    def _verify_guest(self, row, password, address):
        key = guest_key(address, self.settings.blog_comment_hash_secret)
        if password is None:
            raise HTTPException(403, 'Comment password required')
        self._lock('comment-password:' + key)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=10)
        self.db.execute(delete(BlogCommentPasswordAttempt).where(BlogCommentPasswordAttempt.created_at <= cutoff))
        oldest, count = self.db.execute(select(func.min(BlogCommentPasswordAttempt.created_at), func.count()).where(BlogCommentPasswordAttempt.actor_key == key)).one()
        if count >= 5:
            self.db.rollback()
            wait = math.ceil(600 - (now - utc(oldest)).total_seconds())
            raise HTTPException(429, 'Password attempt limit reached', headers={'Retry-After': str(max(1, wait))})
        encoded = row.password_hash
        self.db.add(BlogCommentPasswordAttempt(actor_key=key, created_at=now))
        self.db.commit()  # Deliberately durable even if verification below raises.
        if not verify_password(password.get_secret_value(), encoded or ''):
            raise HTTPException(403, 'Incorrect comment password')

    def _authorize(self, row, user, password, address, deleting):
        if deleting and self._admin(user):
            return
        if row.author_type == 'guest':
            self._verify_guest(row, password, address)
        elif not self._owner(row, user):
            raise HTTPException(403, 'Comment owner required')

    def update(self, slug, identifier, data, user=None, address=''):
        try:
            thread = self._thread(slug)
            row = self._row(identifier, thread)
            if row.deleted_at:
                raise HTTPException(403, 'Deleted comments cannot be edited')
            self._authorize(row, user, data.password, address, deleting=False)
            row = self._row(identifier, thread, lock=True)
            if row.deleted_at:
                raise HTTPException(403, 'Deleted comments cannot be edited')
            row.content, row.updated_at = data.content, datetime.now(timezone.utc)
            self.db.commit()
            return self._public(row, user, slug)
        except Exception:
            self.db.rollback()
            raise

    def delete(self, identifier, slug=None, user=None, password=None, address=''):
        try:
            thread = self._thread(slug) if slug is not None else None
            row = self._row(identifier, thread)
            self._authorize(row, user, password, address, deleting=True)
            row = self._row(identifier, thread, lock=True)
            if row.deleted_at is None:
                row.content = ''
                row.deleted_at = row.updated_at = datetime.now(timezone.utc)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def import_github(self, data):
        """Trusted local operations may call this with a validated GithubImportRequest."""
        try:
            self._lock('comment-github-import')
            pending = list(data.comments)
            imported = skipped = 0
            while pending:
                progressed = False
                for item in list(pending):
                    existing = self.db.scalar(select(BlogComment).where(BlogComment.external_id == item.external_id))
                    if existing:
                        skipped += 1
                    else:
                        thread = canonical_thread(item.thread_slug)
                        if not self.db.scalar(select(BlogPost.id).where(BlogPost.slug.in_([thread, 'en-' + thread]))):
                            raise HTTPException(404, 'Import post not found')
                        parent = None
                        if item.parent_external_id:
                            parent = self.db.scalar(select(BlogComment).where(BlogComment.external_id == item.parent_external_id))
                            if parent is None:
                                continue
                            if parent.thread_slug != thread or parent.parent_id or parent.deleted_at or utc(parent.created_at) >= item.created_at:
                                raise HTTPException(400, 'Invalid imported reply parent')
                        self.db.add(BlogComment(thread_slug=thread, parent_id=parent.id if parent else None,
                                                author_type='github', author_name=item.author_name, content=item.content,
                                                created_at=item.created_at, updated_at=item.created_at,
                                                external_id=item.external_id, source_url=item.source_url))
                        self.db.flush()
                        imported += 1
                    pending.remove(item)
                    progressed = True
                if not progressed:
                    raise HTTPException(400, 'Missing or cyclic imported reply parent')
            self.db.commit()
            return GithubImportResult(imported=imported, skipped=skipped)
        except Exception:
            self.db.rollback()
            raise
