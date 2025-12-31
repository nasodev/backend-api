"""토큰 검증 의존성"""

from typing import Callable

from app.external import verify_id_token as firebase_verify_id_token


# 토큰 검증 함수 타입
TokenVerifier = Callable[[str], dict]

# 기본 토큰 검증 함수 (Firebase 사용)
_token_verifier: TokenVerifier = firebase_verify_id_token


def get_token_verifier() -> TokenVerifier:
    """토큰 검증 함수 반환 (테스트에서 override 가능)"""
    return _token_verifier
