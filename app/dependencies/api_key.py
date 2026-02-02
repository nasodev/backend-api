# app/dependencies/api_key.py
"""API Key 검증 의존성"""

from typing import Optional
from fastapi import Header, HTTPException, status

from app.config import get_settings


def verify_api_key(x_api_key: Optional[str] = Header(None)) -> bool:
    """X-API-Key 헤더 검증

    Args:
        x_api_key: X-API-Key 헤더 값

    Returns:
        True if valid

    Raises:
        HTTPException: 401 if invalid or missing
    """
    settings = get_settings()

    if not x_api_key or x_api_key != settings.ccusage_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return True
