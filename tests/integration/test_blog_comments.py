"""Comment HTTP contract against real persisted SQLite rows; only token verification is faked."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session

from app.main import app
from app.config import get_settings
from app.external.database import Base, get_db
from app.dependencies.token_verifier import get_token_verifier
from tests.unit.services.test_blog_views import add_post, sqlite_jsonb  # SQLite JSONB DDL adapter

ROOT = '/blog/posts/guide/comments'
PASSWORD = ' exact secret password '

@pytest.fixture
def comments(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, 'blog_admin_uids', ['admin'])
    # Allows this contract fixture to run before the feature settings exist.
    monkeypatch.setitem(settings.__dict__, 'blog_comment_hash_secret', 'test-comment-secret')
    monkeypatch.setitem(settings.__dict__, 'blog_comment_trusted_proxy_networks', ['127.0.0.0/8', '::1/128'])
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        for slug in ['guide', 'en-guide', 'other']:
            add_post(db, slug)
        add_post(db, 'draft', published=False)
        add_post(db, 'en-draft')
        db.commit()
        def verify(token):
            if token == 'invalid':
                raise ValueError('Invalid token')
            return {'uid': token, 'name': 'Verified Name', 'email': 'private@example.com',
                    'firebase': {'sign_in_provider': 'password' if token == 'nongoogle' else 'google.com'}}
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_token_verifier] = lambda: verify
        with TestClient(app) as client:
            yield client, db, settings
    app.dependency_overrides.clear()
    engine.dispose()


def trusted_client():
    async def local_transport(scope, receive, send):
        scope['client'] = ('127.0.0.1', 1234)
        await app(scope, receive, send)
    return TestClient(local_transport)


def auth(uid='owner'):
    return {'Authorization': f'Bearer {uid}'}


def create(client, uid='owner', path=ROOT, **extra):
    return client.post(path, headers=auth(uid), json={'content': '<script>alert(1)</script>\n text ', 'author_type': 'google', **extra})


def guest(client, **extra):
    return client.post(ROOT, json={'author_type': 'guest', 'guest_name': ' Visitor ', 'password': PASSWORD, 'content': 'hello', **extra})


def age(db, seconds=16):
    from sqlalchemy import update
    from app.models.blog_comments import BlogComment
    db.execute(update(BlogComment).values(created_at=datetime.now(timezone.utc) - timedelta(seconds=seconds)))
    db.commit()


def test_public_empty_and_private_cache(comments):
    client, _, _ = comments
    response = client.get(ROOT)
    assert response.status_code == 200
    assert response.json() == {'items': [], 'next_cursor': None, 'total': 0}
    assert 'no-store' in response.headers['cache-control']
    assert 'private' in response.headers['cache-control']


def test_google_shared_locales_permissions_and_private_fields(comments):
    client, _, _ = comments
    response = create(client)
    assert response.status_code == 201
    row = response.json()
    assert row['content'] == '<script>alert(1)</script>\n text'
    assert row['author_name'] == 'Verified Name'
    assert row['thread_slug'] == 'guide'
    assert row['can_edit'] is True and row['can_delete'] is True
    assert set(row) == {'id', 'thread_slug', 'parent_id', 'author_type', 'author_name', 'content', 'created_at', 'updated_at', 'is_deleted', 'can_edit', 'can_delete', 'source_url', 'post_slug'}
    page = client.get('/blog/posts/en-guide/comments').json()
    assert page['items'][0]['id'] == row['id']
    assert page['items'][0]['can_edit'] is False
    assert 'private@example.com' not in response.text and 'author_uid' not in response.text
    assert client.get(ROOT, headers=auth('invalid')).status_code == 401
    assert client.get(ROOT, headers={'Authorization': 'Basic bad'}).status_code == 401


@pytest.mark.parametrize('path', ['/blog/posts/missing/comments', '/blog/posts/draft/comments'])
def test_requested_post_must_be_published(comments, path):
    client, _, _ = comments
    assert client.get(path).status_code == 404
    assert create(client, path=path).status_code == 404


def test_google_auth_and_impersonation_rejected(comments):
    client, _, _ = comments
    assert client.post(ROOT, json={'author_type': 'google', 'content': 'hi'}).status_code == 401
    assert create(client, uid='nongoogle').status_code == 403
    assert create(client, author_uid='admin').status_code == 422
    assert create(client, author_name='Imposter').status_code == 422


def test_guest_password_edit_delete_tombstone_and_no_secret_leak(comments):
    client, db, _ = comments
    response = guest(client)
    assert response.status_code == 201
    row = response.json()
    assert row['author_name'] == 'Visitor' and row['can_edit'] is False
    stored = db.execute(text('SELECT author_uid,password_hash,creation_rate_key FROM blog_comments')).one()
    assert stored[0] is None and PASSWORD not in stored[1] and len(stored[2]) == 64
    path = f"{ROOT}/{row['id']}"
    wrong = client.patch(path, json={'content': 'changed', 'password': PASSWORD.strip()})
    assert wrong.status_code == 403 and PASSWORD.strip() not in wrong.text
    good = client.patch(path, json={'content': ' changed ', 'password': PASSWORD})
    assert good.status_code == 200 and good.json()['content'] == 'changed'
    assert client.request('DELETE', path, json={'password': PASSWORD}).status_code == 204
    assert client.request('DELETE', path, json={'password': PASSWORD}).status_code == 204
    marker = client.get(ROOT).json()
    assert marker['total'] == 0
    assert marker['items'][0]['author_name'] == '' and marker['items'][0]['content'] == ''
    assert marker['items'][0]['is_deleted'] is True
    assert client.patch(path, json={'content': 'restore', 'password': PASSWORD}).status_code == 403


@pytest.mark.parametrize('payload', [
    {'password': ' ' * 9}, {'password': 'x' * 129},
    {'password': {'secret': 'raw-secret'}}, {'content': ' '}, {'content': 'x' * 5001},
    {'guest_name': ' '}, {'guest_name': 'x' * 41}, {'author_uid': 'raw-secret'},
])
def test_invalid_guest_inputs_never_echo_password(comments, payload):
    client, _, _ = comments
    response = guest(client, **payload)
    assert response.status_code == 422
    assert PASSWORD not in response.text and 'raw-secret' not in response.text and 'x' * 129 not in response.text


def test_short_password_and_guest_mode_with_token(comments):
    client, db, _ = comments
    response = guest(client, password='short')
    assert response.status_code == 422 and 'short' not in response.text
    response = client.post(ROOT, headers=auth(), json={'author_type': 'guest', 'guest_name': 'Guest', 'password': PASSWORD, 'content': 'hey'})
    assert response.status_code == 201
    assert db.execute(text('SELECT author_uid FROM blog_comments')).scalar() is None


def test_owners_and_admin_delete_only(comments):
    client, _, _ = comments
    row = create(client).json()
    path = f"{ROOT}/{row['id']}"
    assert client.patch(path, headers=auth('other'), json={'content': 'bad'}).status_code == 403
    assert client.patch(path, headers=auth('admin'), json={'content': 'bad'}).status_code == 403
    assert client.delete(path, headers=auth('other')).status_code == 403
    assert client.patch(path, headers=auth(), json={'content': 'edited'}).json()['content'] == 'edited'
    assert client.delete(path, headers=auth('admin')).status_code == 204
    assert client.delete(path, headers=auth()).status_code == 204


def test_replies_cross_thread_depth_and_deleted_parent(comments):
    client, _, _ = comments
    root = create(client).json()
    assert create(client, uid='two', path='/blog/posts/other/comments', parent_id=root['id']).status_code == 400
    assert client.patch(f"/blog/posts/other/comments/{root['id']}", headers=auth(), json={'content': 'bad'}).status_code == 404
    assert client.delete(f"/blog/posts/other/comments/{root['id']}", headers=auth()).status_code == 404
    reply = create(client, uid='two', parent_id=root['id'])
    assert reply.status_code == 201
    assert create(client, uid='three', parent_id=reply.json()['id']).status_code == 400
    assert client.delete(f"{ROOT}/{root['id']}", headers=auth()).status_code == 204
    assert create(client, uid='three', parent_id=root['id']).status_code == 400
    page = client.get(ROOT).json()
    assert page['total'] == 1 and len(page['items']) == 2


def test_creation_throttle_counts_deleted_rows(comments):
    client, db, _ = comments
    row = create(client).json()
    client.delete(f"{ROOT}/{row['id']}", headers=auth())
    response = create(client)
    assert response.status_code == 429 and int(response.headers['retry-after']) > 0
    age(db)
    assert create(client).status_code == 201


def test_guest_throttle_untrusted_header_and_missing_secret(comments):
    client, _, settings = comments
    assert guest(client).status_code == 201
    response = client.post(ROOT, headers={'X-Real-IP': '203.0.113.42'}, json={'author_type': 'guest', 'guest_name': 'Another', 'password': PASSWORD, 'content': 'bypass'})
    assert response.status_code == 429
    settings.blog_comment_hash_secret = ''
    assert guest(client).status_code == 503


def test_wrong_password_attempts_are_durable_and_global(comments):
    client, db, settings = comments
    first = guest(client).json()
    age(db)
    second = guest(client).json()
    for index in range(5):
        target = [first, second][index % 2]
        response = client.patch(f"{ROOT}/{target['id']}", json={'content': 'attack', 'password': 'wrong-password'})
        assert response.status_code == 403
        # An exception must not roll back recorded attempts.
        db.rollback()
    response = client.patch(f"{ROOT}/{first['id']}", json={'content': 'valid', 'password': PASSWORD})
    assert response.status_code == 429 and int(response.headers['retry-after']) > 0
    settings.blog_comment_hash_secret = ''
    assert client.patch(f"{ROOT}/{first['id']}", json={'content': 'valid', 'password': PASSWORD}).status_code == 503


def test_chronological_pagination_and_malformed_cursor(comments):
    client, _, _ = comments
    ids = [create(client, uid=f'u{i}').json()['id'] for i in range(3)]
    first = client.get(ROOT, params={'limit': 2}).json()
    assert [r['id'] for r in first['items']] == ids[:2] and first['total'] == 3
    second = client.get(ROOT, params={'limit': 2, 'cursor': first['next_cursor']}).json()
    assert [r['id'] for r in second['items']] == ids[2:] and second['next_cursor'] is None
    assert client.get(ROOT, params={'cursor': 'garbage'}).status_code == 400
    assert client.get(ROOT, params={'limit': 51}).status_code == 422


def import_item(external='gh-1', **extra):
    return {'external_id': external, 'thread_slug': 'guide', 'author_name': 'nasodev', 'content': 'test', 'created_at': '2025-11-16T12:00:00Z', 'source_url': 'https://github.com/nasodev/blog/discussions/1#discussioncomment-123', **extra}


def test_admin_import_idempotent_parent_order_and_ownership(comments):
    client, _, _ = comments
    path = '/blog/admin/comments/import-github'
    payload = {'comments': [import_item('reply', parent_external_id='gh-1', created_at='2025-11-16T13:00:00Z'), import_item()]}
    assert client.post(path, headers=auth('other'), json=payload).status_code == 403
    assert client.post(path, headers=auth('admin'), json=payload).json() == {'imported': 2, 'skipped': 0}
    assert client.post(path, headers=auth('admin'), json=payload).json() == {'imported': 0, 'skipped': 2}
    rows = client.get(ROOT).json()['items']
    assert rows[0]['author_type'] == 'github' and rows[0]['author_name'] == 'nasodev'
    assert rows[0]['created_at'].startswith('2025-11-16T12:00:00')
    assert rows[1]['parent_id'] == rows[0]['id']
    assert client.patch(f"{ROOT}/{rows[0]['id']}", headers=auth('nasodev'), json={'content': 'bad'}).status_code == 403
    assert client.get('/blog/admin/comments', headers=auth('other')).status_code == 403
    admin = client.get('/blog/admin/comments', headers=auth('admin'), params={'limit': 1}).json()
    assert admin['items'][0]['id'] == rows[1]['id']
    assert client.delete(f"/blog/admin/comments/{rows[0]['id']}", headers=auth('admin')).status_code == 204


@pytest.mark.parametrize('url', ['https://evil.test/a', 'https://github.com.evil.test/a/b/discussions/1', 'https://github.com/a/b/issues/1', 'javascript:alert(1)'])
def test_import_source_allowlist(comments, url):
    client, _, _ = comments
    assert client.post('/blog/admin/comments/import-github', headers=auth('admin'), json={'comments': [import_item(source_url=url)]}).status_code == 422


@pytest.mark.parametrize('cursor', ['', 'WzEsMl0=', 'bnVsbA==', 'eyJhIjoxfQ==', 'x' * 1025])
def test_all_malformed_cursor_shapes_are_400(comments, cursor):
    client, _, _ = comments
    assert client.get(ROOT, params={'cursor': cursor}).status_code == 400


def test_guest_invalid_parent_and_rate_checks_precede_hashing(comments, monkeypatch):
    from app.services.blog import comments as service_module
    client, _, _ = comments
    assert guest(client).status_code == 201
    def unexpected_hash(_password):
        pytest.fail('Hashing must not run before rejecting an exhausted creation budget')
    monkeypatch.setattr(service_module, 'hash_password', unexpected_hash)
    assert guest(client).status_code == 429
    # Different IP through an explicitly trusted test transport enables a fresh actor.
    with trusted_client() as trusted:
        assert trusted.post(ROOT, headers={'X-Real-IP': '203.0.113.10'}, json={
            'author_type': 'guest', 'guest_name': 'A', 'password': PASSWORD,
            'content': 'hello', 'parent_id': str(uuid4()),
        }).status_code == 400


def test_password_limit_precedes_hash_verification_and_expires(comments, monkeypatch):
    from app.models.blog_comments import BlogCommentPasswordAttempt
    from app.services.blog import comments as service_module
    from sqlalchemy import update
    client, db, _ = comments
    row = guest(client).json()
    path = f"{ROOT}/{row['id']}"
    for _ in range(5):
        assert client.patch(path, json={'content': 'x', 'password': 'wrong-password'}).status_code == 403
    original = service_module.verify_password
    def unexpected_verify(*_args):
        pytest.fail('Password verification ran after the durable budget was exhausted')
    monkeypatch.setattr(service_module, 'verify_password', unexpected_verify)
    assert client.patch(path, json={'content': 'x', 'password': PASSWORD}).status_code == 429
    db.execute(update(BlogCommentPasswordAttempt).values(created_at=datetime.now(timezone.utc) - timedelta(minutes=11)))
    db.commit()
    monkeypatch.setattr(service_module, 'verify_password', original)
    assert client.patch(path, json={'content': 'now permitted', 'password': PASSWORD}).status_code == 200
    assert db.execute(text('SELECT COUNT(*) FROM blog_comment_password_attempts')).scalar() == 1


def test_daily_creation_cap_and_rolling_expiry(comments):
    from app.models.blog_comments import BlogComment
    from sqlalchemy import select, update
    client, db, _ = comments
    first = create(client).json()
    stored = db.scalar(select(BlogComment).where(BlogComment.id == UUID(first['id'])))
    now = datetime.now(timezone.utc)
    stored.created_at = now - timedelta(hours=1)
    for _ in range(99):
        db.add(BlogComment(thread_slug='guide', author_type='google', author_uid='owner', author_name='Name', content='',
                           creation_rate_key=stored.creation_rate_key, created_at=now - timedelta(hours=1), deleted_at=now))
    db.commit()
    response = create(client)
    assert response.status_code == 429 and int(response.headers['retry-after']) > 80000
    db.execute(update(BlogComment).values(created_at=now - timedelta(days=1, seconds=1)))
    db.commit()
    assert create(client).status_code == 201


def test_trusted_proxy_uses_valid_real_ip_only(comments):
    _, _, _ = comments
    body = {'author_type': 'guest', 'guest_name': 'Guest', 'password': PASSWORD, 'content': 'hi'}
    with trusted_client() as client:
        assert client.post(ROOT, json=body, headers={'X-Real-IP': '203.0.113.1'}).status_code == 201
        assert client.post(ROOT, json=body, headers={'X-Real-IP': '203.0.113.2'}).status_code == 201
        assert client.post(ROOT, json=body, headers={'X-Real-IP': '203.0.113.1'}).status_code == 429
        assert client.post(ROOT, json=body, headers={'X-Real-IP': 'invalid'}).status_code == 201
        assert client.post(ROOT, json=body, headers={'X-Real-IP': 'also-invalid'}).status_code == 429


def test_same_timestamp_paging_and_cross_scope_cursor(comments):
    from app.models.blog_comments import BlogComment
    from sqlalchemy import update
    client, db, _ = comments
    ids = sorted(create(client, uid=f'tie-{i}').json()['id'] for i in range(3))
    db.execute(update(BlogComment).values(created_at=datetime(2026, 1, 1, tzinfo=timezone.utc)))
    db.commit()
    first = client.get(ROOT, params={'limit': 2}).json()
    assert [row['id'] for row in first['items']] == ids[:2]
    assert client.get('/blog/posts/other/comments', params={'cursor': first['next_cursor']}).status_code == 400
    second = client.get(ROOT, params={'cursor': first['next_cursor']}).json()
    assert [row['id'] for row in second['items']] == ids[2:]


def test_admin_can_moderate_orphan_thread_and_guest_without_secret(comments):
    from app.models.blog import BlogPost
    from sqlalchemy import delete
    client, db, settings = comments
    row = guest(client).json()
    settings.blog_comment_hash_secret = ''
    db.execute(delete(BlogPost).where(BlogPost.slug.in_(['guide', 'en-guide'])))
    db.commit()
    assert client.get(ROOT).status_code == 404
    assert client.delete(f"/blog/admin/comments/{row['id']}", headers=auth('admin')).status_code == 204
    assert client.get('/blog/admin/comments', headers=auth('admin')).json()['items'][0]['is_deleted'] is True


def test_import_is_atomic_for_missing_parent_and_cross_thread_parent(comments):
    client, db, _ = comments
    path = '/blog/admin/comments/import-github'
    for child in [import_item('reply', parent_external_id='missing'), import_item('reply', parent_external_id='gh-1', thread_slug='other')]:
        response = client.post(path, headers=auth('admin'), json={'comments': [import_item(), child]})
        assert response.status_code == 400
        assert db.execute(text('SELECT COUNT(*) FROM blog_comments')).scalar() == 0


def test_model_level_errors_and_invalid_json_do_not_echo_password(comments):
    client, _, _ = comments
    for body in [
        {'author_type': 'guest', 'content': 'hi', 'password': PASSWORD},
        {'author_type': 'guest', 'content': 'hi', 'guest_name': 'Guest'},
    ]:
        response = client.post(ROOT, json=body)
        assert response.status_code == 422 and PASSWORD not in response.text
    response = client.post(ROOT, content='{"password": "leak-me-secret", invalid}', headers={'Content-Type': 'application/json'})
    assert response.status_code == 422 and 'leak-me-secret' not in response.text


def test_admin_article_links_prefer_published_ko_then_english(comments):
    from app.models.blog import BlogPost
    from sqlalchemy import update
    client, db, _ = comments
    row = create(client).json()
    assert row['post_slug'] == 'guide'
    assert client.get('/blog/posts/en-guide/comments').json()['items'][0]['post_slug'] == 'en-guide'
    assert client.get('/blog/admin/comments', headers=auth('admin')).json()['items'][0]['post_slug'] == 'guide'
    db.execute(update(BlogPost).where(BlogPost.slug == 'guide').values(is_published=False))
    db.commit()
    assert client.get('/blog/admin/comments', headers=auth('admin')).json()['items'][0]['post_slug'] == 'en-guide'
    db.execute(update(BlogPost).where(BlogPost.slug == 'en-guide').values(is_published=False))
    db.commit()
    assert client.get('/blog/admin/comments', headers=auth('admin')).json()['items'][0]['post_slug'] is None


@pytest.mark.parametrize('identifier', [123, {}, ['bad']])
def test_cursor_uuid_must_be_a_string(comments, identifier):
    import base64
    import json
    client, _, _ = comments
    cursor = base64.urlsafe_b64encode(json.dumps(['thread:guide', '2026-01-01T00:00:00Z', identifier]).encode()).decode()
    assert client.get(ROOT, params={'cursor': cursor}).status_code == 400


def test_private_cache_headers_on_auth_error(comments):
    client, _, _ = comments
    response = client.get(ROOT, headers=auth('invalid'))
    assert response.status_code == 401
    assert response.headers.get('cache-control') == 'private, no-store'


def test_single_comment_refreshes_viewer_permissions_without_private_fields(comments):
    client, _, _ = comments
    created = create(client).json()
    path = f"{ROOT}/{created['id']}"
    anonymous = client.get(path)
    assert anonymous.status_code == 200
    assert anonymous.headers['cache-control'] == 'private, no-store'
    assert anonymous.headers['vary'] == 'Authorization'
    assert set(anonymous.json()) == set(created)
    assert anonymous.json()['can_edit'] is False and anonymous.json()['can_delete'] is False
    assert anonymous.json()['content'] == created['content']
    owner = client.get(path, headers=auth())
    assert owner.status_code == 200
    assert owner.json()['can_edit'] is True and owner.json()['can_delete'] is True
    other = client.get(path, headers=auth('other')).json()
    assert other['can_edit'] is False and other['can_delete'] is False
    admin = client.get(path, headers=auth('admin')).json()
    assert admin['can_edit'] is False and admin['can_delete'] is True
    english = client.get(f"/blog/posts/en-guide/comments/{created['id']}").json()
    assert english['id'] == created['id'] and english['post_slug'] == 'en-guide'
    assert 'author_uid' not in owner.text and 'private@example.com' not in owner.text


def test_single_comment_checks_requested_language_thread_and_missing_ids(comments):
    from sqlalchemy import update
    from app.models.blog import BlogPost
    client, db, _ = comments
    created = create(client).json()
    assert client.get(f"/blog/posts/other/comments/{created['id']}").status_code == 404
    assert client.get(f"{ROOT}/{uuid4()}").status_code == 404
    assert client.get(f"/blog/posts/missing/comments/{created['id']}").status_code == 404
    db.execute(update(BlogPost).where(BlogPost.slug == 'guide').values(is_published=False))
    db.commit()
    assert client.get(f"{ROOT}/{created['id']}", headers=auth('admin')).status_code == 404
    assert client.get(f"/blog/posts/en-guide/comments/{created['id']}").status_code == 200


def test_single_comment_rejects_invalid_optional_auth_and_returns_tombstone(comments):
    client, _, _ = comments
    created = create(client).json()
    path = f"{ROOT}/{created['id']}"
    invalid = client.get(path, headers=auth('invalid'))
    assert invalid.status_code == 401
    assert invalid.headers['cache-control'] == 'private, no-store'
    assert client.get(path, headers={'Authorization': 'Basic bad'}).status_code == 401
    assert client.delete(path, headers=auth()).status_code == 204
    marker = client.get(path, headers=auth())
    assert marker.status_code == 200
    assert marker.json()['is_deleted'] is True
    assert marker.json()['author_name'] == marker.json()['content'] == ''
    assert marker.json()['can_edit'] is False and marker.json()['can_delete'] is False
