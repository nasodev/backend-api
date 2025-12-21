import firebase_admin
from firebase_admin import credentials, auth
from pathlib import Path

from app.config import get_settings

settings = get_settings()

# Firebase Admin SDK 초기화
_firebase_app = None


def get_firebase_app():
    """Firebase Admin SDK 앱 인스턴스 반환 (싱글톤)"""
    global _firebase_app

    if _firebase_app is None:
        cred_path = Path(settings.firebase_credentials_path)
        if not cred_path.exists():
            raise FileNotFoundError(f"Firebase credentials not found: {cred_path}")

        cred = credentials.Certificate(str(cred_path))
        _firebase_app = firebase_admin.initialize_app(cred)

    return _firebase_app


def verify_id_token(id_token: str) -> dict:
    """
    Firebase ID Token 검증

    Args:
        id_token: Firebase ID Token

    Returns:
        dict: 디코딩된 토큰 정보 (uid, email 등)

    Raises:
        firebase_admin.auth.InvalidIdTokenError: 유효하지 않은 토큰
        firebase_admin.auth.ExpiredIdTokenError: 만료된 토큰
    """
    # Firebase 앱 초기화 확인
    get_firebase_app()

    # 토큰 검증
    decoded_token = auth.verify_id_token(id_token)
    return decoded_token
