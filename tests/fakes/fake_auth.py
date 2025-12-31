"""Fake 인증 서비스"""


class FakeAuthService:
    """테스트용 Fake 토큰 검증 서비스

    Usage:
        fake_auth = FakeAuthService()
        fake_auth.set_success("user-123", "user@example.com", "User Name")
        # 또는
        fake_auth.set_failure("expired")  # 만료된 토큰 시뮬레이션

        app.dependency_overrides[get_token_verifier] = lambda: fake_auth.verify_token
    """

    def __init__(
        self,
        uid: str = "test-uid",
        email: str = "test@example.com",
        name: str = "Test User",
    ):
        self.uid = uid
        self.email = email
        self.name = name
        self._should_fail = False
        self._error_type = None

    def set_success(self, uid: str, email: str = None, name: str = None):
        """성공 응답 설정"""
        self.uid = uid
        self.email = email if email else self.email
        self.name = name if name else self.name
        self._should_fail = False

    def set_failure(self, error_type: str = "invalid"):
        """실패 응답 설정

        Args:
            error_type: "invalid" | "expired" | "auth_error"
        """
        self._should_fail = True
        self._error_type = error_type

    def verify_token(self, token: str) -> dict:
        """토큰 검증 (Fake) - TokenVerifier 타입과 호환

        Args:
            token: Bearer 토큰 (테스트에서는 무시됨)

        Returns:
            dict: 디코딩된 토큰 정보

        Raises:
            firebase_auth.ExpiredIdTokenError: error_type="expired"
            firebase_auth.InvalidIdTokenError: error_type="invalid"
            Exception: error_type="auth_error"
        """
        if self._should_fail:
            if self._error_type == "expired":
                from firebase_admin import auth as firebase_auth

                raise firebase_auth.ExpiredIdTokenError("Token expired", cause=None)
            elif self._error_type == "auth_error":
                raise Exception("Authentication service unavailable")
            else:
                from firebase_admin import auth as firebase_auth

                raise firebase_auth.InvalidIdTokenError("Invalid token")

        return {
            "uid": self.uid,
            "email": self.email,
            "name": self.name,
        }
