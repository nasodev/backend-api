"""인증 관련 도메인 엔티티"""


class FirebaseUser:
    """Firebase 인증 사용자 정보"""

    def __init__(self, uid: str, email: str | None, name: str | None, token_data: dict):
        self.uid = uid
        self.email = email
        self.name = name
        self.token_data = token_data

    def __repr__(self):
        return f"FirebaseUser(uid={self.uid}, email={self.email}, name={self.name})"
