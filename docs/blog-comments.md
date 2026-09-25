# Native blog comments

Comments use PostgreSQL and the existing Firebase verifier. Korean `slug` and English
`en-slug` share a thread, but every public operation first checks the exact requested
post is published. Comment rows have no foreign key to a translation row, so deleting
one translation preserves the conversation. Only one reply level is supported.

## Configuration and rollout

Set a dedicated, stable, random `BLOG_COMMENT_HASH_SECRET` before enabling guest
writes. Keep this value in the deployment secret/environment store. Guest creation
and password verification return 503 if it is absent. Google comments continue to
work. No IP address is stored: the guest actor key is HMAC-SHA256 of its address.

`BLOG_COMMENT_TRUSTED_PROXY_NETWORKS` is a JSON array of CIDRs and defaults to
`["127.0.0.0/8", "::1/128"]`. Only a direct peer in one of these networks may supply
`X-Real-IP`; all other forwarded headers are ignored. Set Nginx to overwrite
`X-Real-IP` with its actual client address. For this production Docker network,
verify the gateway first and add `172.19.0.1/32`; never trust all private networks.
Ensure the application server preserves the direct peer address. In particular,
disable Uvicorn's automatic proxy-header interpretation (`--no-proxy-headers`)
when Nginx supplies X-Real-IP, so the application owns this trust decision. The
Docker, systemd and local launch commands set this flag. It also leaves the ASGI
scheme as the upstream HTTP transport; use canonical API paths without trailing
slashes (or terminate any redirects at the HTTPS proxy). No application route uses
the peer/scheme to build redirects. The existing Docker gateway was not covered by
Uvicorn’s default loopback trust, so this does not change its production scheme.

1. Deploy the backend and configure the secret/proxy peers.
2. Apply `alembic upgrade head` through the existing migration process. Revision
   `a381e14d3e7f` follows `707aae763c56` and only adds the comment and password-attempt
   tables/indexes; it does not rewrite posts or view counts.
3. Import the backed-up GitHub data and verify it by a public GET.
4. Deploy the frontend. Keep the original GitHub discussion unchanged.

The offline migration preview needs no database connection:
`python -m alembic upgrade 707aae763c56:head --sql`.
Downgrading drops the comment tables and loses their data; preserve a backup first.

## API

All paths below start with `/blog`. Public requests accept an optional Firebase
Bearer token. Invalid supplied tokens are rejected. Google writes require the
verified `google.com` sign-in provider. UID and display name come from that token;
client UID/privilege fields are forbidden. Guests supply their nickname and a
per-comment password; a simultaneously supplied valid token does not own the row.

| Method | Path | Behavior |
| --- | --- | --- |
| GET | `/posts/{slug}/comments` | Oldest first, `limit=20` (max 50), optional cursor |
| GET | `/posts/{slug}/comments/{id}` | One same-thread comment with current viewer permissions |
| POST | `/posts/{slug}/comments` | `{author_type, content, parent_id?, guest_name?, password?}`; 201 |
| PATCH | `/posts/{slug}/comments/{id}` | `{content, password?}`; owner or guest password; 200 |
| DELETE | `/posts/{slug}/comments/{id}` | Optional `{password}`; owner, guest password, or admin; 204 |
| GET | `/admin/comments` | Existing blog-admin auth; newest first across threads |
| DELETE | `/admin/comments/{id}` | Existing blog-admin auth, even for unpublished/orphan threads |
| POST | `/admin/comments/import-github` | Existing blog-admin auth; import up to 100 rows |

Pages are `{items, next_cursor, total}`. Total counts active comments/replies, while
items include deleted markers. Cursors are scoped to the thread or admin list and
order by `(created_at, id)`. A comment returns `id`, `thread_slug`, `parent_id`,
`author_type`, `author_name`, `content`, `created_at`, `updated_at`, `is_deleted`,
`can_edit`, `can_delete`, `source_url`, and nullable `post_slug`. Public operations
return their requested post slug. Admin pages batch-resolve a published Korean
slug, then English, or null if neither exists. No UID, email, password hash or rate
key is serialized. All comment responses include `Cache-Control: private, no-store`.

`can_edit`/`can_delete` describe token-authorized actions; anonymous guest password
forms can be offered based on `author_type == "guest"`. Admins can delete others'
comments but cannot edit them. Delete clears the body and returns a nameless marker,
keeps existing replies and prevents further edits/new replies; authorized repeated
deletes are successful. Guest retries still consume the password verification budget.

Content is trimmed plain text (1–5000 characters), with line breaks preserved. Guest
names are trimmed (1–40). Passwords are 8–128 characters, not all whitespace, and
are **not trimmed**. Store no passwords in browser storage. Rendering must use text,
never submitted HTML. Passwords use random 16-byte salts and versioned PBKDF2-HMAC-
SHA256 with 600,000 iterations and constant-time digest comparison. SecretStr inputs
and a comment-specific validation handler prevent password echoing in 422 errors.

New comments/replies are limited to one every 15 seconds and 100 per rolling 24
hours per Google UID or guest address; deleted rows count. Actor checks/inserts use
deterministic SHA256-derived signed 64-bit PostgreSQL transaction advisory locks.
Guest password verification permits five attempts per ten minutes per address
across all comments. Attempts are committed **before** KDF verification, including
wrong passwords; expired attempts are pruned. The sixth request does no KDF work.
These are database limits, shared by API processes. SQLite tests skip only the
PostgreSQL-specific advisory lock. 429 responses include `Retry-After` seconds.

## GitHub import and local operations

The HTTP payload is `{ "comments": [...] }`. Each item has `external_id`,
`thread_slug`, `author_name`, `content`, `created_at` (timezone-aware original date),
`source_url`, and optional `parent_external_id`. URLs must be HTTPS GitHub discussion
or discussion-comment URLs. A post in the canonical thread must exist (drafts are
allowed). Original names, content and timestamps are preserved without a Google UID.
Import is atomic, serializes imports, supports parents later in the input, and skips
existing external IDs without modifying them. Replies must point to an older root
in the same thread. Missing/cyclic parents reject the batch.

For an operations shell **inside the backend container**, normalize the saved
GitHub snapshot into that payload and invoke the same validated service directly:

```python
import json
from pathlib import Path
from app.external.database import SessionLocal
from app.schemas.blog_comments import GithubImportRequest
from app.services.blog.comments import CommentService

payload = GithubImportRequest.model_validate_json(Path('/tmp/comments-import.json').read_text())
with SessionLocal() as db:
    result = CommentService(db).import_github(payload)
    print(result.model_dump_json())
```

No Firebase token is needed for this trusted local operation. This method commits
its own transaction; use a dedicated session with no unrelated pending writes.
Repeating the same input returns `{ "imported": 0, "skipped": N }`. Do not send a
synthetic public comment as a deployment test.

## Verification

Run `python -m pytest -q` with a test database URL in the environment. New tests use
real ORM queries and persistence on disposable SQLite; token verification alone is
faked for HTTP scenarios. Coverage includes permissions, shared locales/drafts,
tombstones, guest secret non-disclosure, durable guessing limits and KDF ordering,
trusted proxy behavior, rate limits including deletes, malformed/scoped cursors,
admin links and idempotent/atomic imports. PostgreSQL advisory-lock concurrency is
not exercised by SQLite; migration SQL is separately rendered for PostgreSQL.
