"""Exercise the real KDF and address trust boundary, including malformed inputs."""
import pytest
from starlette.requests import Request

from app.services.blog.comment_security import client_address, hash_password, verify_password


def test_password_salts_are_unique_and_exact_password_is_required():
    password = ' exact password '
    first, second = hash_password(password), hash_password(password)
    assert first != second
    assert first.startswith('v1$pbkdf2-sha256$600000$')
    assert password not in first
    assert verify_password(password, first)
    assert verify_password(password, second)
    assert not verify_password(password.strip(), first)
    assert not verify_password('incorrect password', first)


@pytest.mark.parametrize('stored', ['', 'v2$pbkdf2-sha256$600000$a$b', 'v1$pbkdf2-sha256$999999999$a$b', 'v1$pbkdf2-sha256$600000$zz$zz'])
def test_malformed_password_hashes_fail_closed(stored):
    assert not verify_password('some password', stored)


@pytest.mark.parametrize('peer,header,trusted,expected', [
    ('203.0.113.1', '203.0.113.99', ['127.0.0.0/8'], '203.0.113.1'),
    ('172.19.0.1', '203.0.113.99', ['172.19.0.1/32'], '203.0.113.99'),
    ('172.19.0.2', '203.0.113.99', ['172.19.0.1/32'], '172.19.0.2'),
    ('::1', '2001:db8::1', ['::1/128'], '2001:db8::1'),
    ('::1', '203.0.113.1, 203.0.113.2', ['::1/128'], '::1'),
])
def test_only_explicit_direct_proxy_networks_can_supply_real_ip(peer, header, trusted, expected):
    request = Request({'type': 'http', 'client': (peer, 1234), 'headers': [(b'x-real-ip', header.encode())]})
    assert client_address(request, trusted) == expected


def test_settings_hide_hash_secret():
    from app.config import Settings
    config = Settings(database_url='sqlite://', blog_comment_hash_secret='private-hash-secret')
    assert 'private-hash-secret' not in repr(config)


def test_settings_reject_invalid_proxy_networks():
    from pydantic import ValidationError
    from app.config import Settings
    with pytest.raises(ValidationError):
        Settings(database_url='sqlite://', blog_comment_trusted_proxy_networks=['not-a-cidr'])
