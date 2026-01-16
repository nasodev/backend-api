"""전역 예외 핸들러"""

from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.exceptions import NotFoundError, DuplicateError, ForbiddenError


async def not_found_error_handler(request: Request, exc: NotFoundError):
    """NotFoundError → 404 응답"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": exc.message},
    )


async def duplicate_error_handler(request: Request, exc: DuplicateError):
    """DuplicateError → 400 응답"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message},
    )


async def forbidden_error_handler(request: Request, exc: ForbiddenError):
    """ForbiddenError → 403 응답"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": exc.message},
    )


def register_exception_handlers(app):
    """FastAPI 앱에 예외 핸들러 등록"""
    app.add_exception_handler(NotFoundError, not_found_error_handler)
    app.add_exception_handler(DuplicateError, duplicate_error_handler)
    app.add_exception_handler(ForbiddenError, forbidden_error_handler)
