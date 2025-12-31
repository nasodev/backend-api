"""인증 서비스 인터페이스 정의"""

from typing import Protocol


class AuthServiceProtocol(Protocol):
    """인증 서비스 인터페이스 (TDD용 추상화)"""

    def verify_token(self, token: str) -> dict:
        """
        토큰 검증

        Args:
            token: 인증 토큰

        Returns:
            dict: 디코딩된 토큰 정보 (uid, email 등)

        Raises:
            인증 실패 시 예외
        """
        ...
