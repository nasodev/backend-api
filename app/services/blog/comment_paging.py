"""Opaque, scoped chronological cursors; never used to choose the thread."""
import base64
import binascii
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException


def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def encode_cursor(row, scope):
    payload = [scope, utc(row.created_at).isoformat(), str(row.id)]
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')


def decode_cursor(value, scope):
    try:
        if len(value) > 1024:
            raise ValueError()
        decoded = json.loads(base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True))
        if (not isinstance(decoded, list) or len(decoded) != 3
                or not all(isinstance(part, str) for part in decoded) or decoded[0] != scope):
            raise ValueError()
        stamp = datetime.fromisoformat(decoded[1])
        if stamp.tzinfo is None:
            raise ValueError()
        return utc(stamp), UUID(decoded[2])
    except (ValueError, TypeError, binascii.Error, UnicodeError):
        raise HTTPException(400, 'Invalid comment cursor') from None
