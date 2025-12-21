from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth

from app.firebase import verify_id_token

# Bearer 토큰 스키마
security = HTTPBearer()


class FirebaseUser:
    """Firebase 인증 사용자 정보"""

    def __init__(self, uid: str, email: str | None, name: str | None, token_data: dict):
        self.uid = uid
        self.email = email
        self.name = name
        self.token_data = token_data

    def __repr__(self):
        return f"FirebaseUser(uid={self.uid}, email={self.email}, name={self.name})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
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
        decoded_token = verify_id_token(token)

        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email"),
            name=decoded_token.get("name"),
            token_data=decoded_token,
        )

    except firebase_auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
