"""공통 예외 클래스"""


class AppError(Exception):
    """애플리케이션 기본 예외"""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    """리소스를 찾을 수 없음 (404)"""
    pass


class DuplicateError(AppError):
    """중복된 리소스 (400/409)"""
    pass


class ForbiddenError(AppError):
    """권한 없음 (403)"""
    pass
