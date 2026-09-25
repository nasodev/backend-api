"""Password hashing and explicitly bounded proxy trust; no raw address is stored."""
import hashlib
import hmac
import ipaddress
import secrets

from fastapi import HTTPException, Request

ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
    return f'v1$pbkdf2-sha256${ITERATIONS}${salt.hex()}${digest.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        version, algorithm, iterations, salt_hex, digest_hex = encoded.split('$')
        if (version, algorithm, iterations) != ('v1', 'pbkdf2-sha256', str(ITERATIONS)):
            return False
        salt, expected = bytes.fromhex(salt_hex), bytes.fromhex(digest_hex)
        if len(salt) != 16 or len(expected) != 32:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, ITERATIONS)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def client_address(request: Request, trusted_networks: list[str]) -> str:
    peer = request.client.host if request.client else ''
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        # ASGI test transports may use a hostname; production peers are IPs.
        return peer
    if any(address in ipaddress.ip_network(network) for network in trusted_networks):
        forwarded = request.headers.get('x-real-ip')
        if forwarded:
            try:
                return str(ipaddress.ip_address(forwarded))
            except ValueError:
                pass
    return str(address)


def guest_key(address: str, secret: str) -> str:
    if not secret:
        raise HTTPException(503, 'Guest comment protection is unavailable')
    if not address:
        raise HTTPException(503, 'Client address is unavailable')
    return hmac.new(secret.encode(), address.encode(), hashlib.sha256).hexdigest()
