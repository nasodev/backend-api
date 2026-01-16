"""인증 의존성 구현"""

import logging
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth

from app.dependencies.entities import FirebaseUser
from app.dependencies.token_verifier import get_token_verifier, TokenVerifier

logger = logging.getLogger(__name__)

# Bearer 토큰 스키마
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    verify_token: TokenVerifier = Depends(get_token_verifier),
) -> FirebaseUser:
    """
    Firebase ID Token을 검증하고 사용자 정보 반환

    Usage:
        @router.get("/protected")
        def protected_route(user: FirebaseUser = Depends(get_current_user)):
            return {"uid": user.uid}
    """
    token = credentials.credentials

    try:
        decoded_token = verify_token(token)

        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email"),
            name=decoded_token.get("name"),
            token_data=decoded_token,
        )

    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        # 내부 로깅 (디버깅용)
        logger.error(f"Authentication error: {type(e).__name__}: {str(e)}")
        # 클라이언트에는 일반적인 메시지만 반환 (정보 누출 방지)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
