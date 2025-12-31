"""Fake 데이터베이스 세션"""

from sqlalchemy.exc import OperationalError


class FakeDatabase:
    """테스트용 Fake DB 세션"""

    def __init__(self):
        self._should_fail = False
        self._error_message = None
        self._execute_count = 0

    def set_success(self):
        """성공 상태 설정"""
        self._should_fail = False

    def set_connection_error(self, message: str = "could not connect to server"):
        """연결 오류 설정"""
        self._should_fail = True
        self._error_message = message

    def execute(self, query):
        """쿼리 실행 (Fake)"""
        self._execute_count += 1
        if self._should_fail:
            raise OperationalError(
                statement="SELECT 1",
                params={},
                orig=Exception(self._error_message),
            )
        return None

    def close(self):
        """세션 닫기"""
        pass

    @property
    def execute_count(self) -> int:
        """실행 횟수"""
        return self._execute_count
