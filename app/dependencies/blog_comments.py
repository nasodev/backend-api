"""Optional authentication never silently ignores a supplied invalid token."""
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.config import get_settings
from app.dependencies.auth import get_current_user
from app.dependencies.token_verifier import get_token_verifier, TokenVerifier
from app.external.database import get_db
from app.services.blog.comments import CommentService


async def optional_comment_user(request: Request, verify: TokenVerifier = Depends(get_token_verifier)):
    value = request.headers.get('authorization')
    if value is None:
        return None
    scheme, _, token = value.partition(' ')
    if scheme.lower() != 'bearer' or not token.strip():
        raise HTTPException(401, 'Invalid authentication token')
    return await get_current_user(HTTPAuthorizationCredentials(scheme='Bearer', credentials=token), verify)


def get_comment_service(db: Session = Depends(get_db)):
    return CommentService(db, get_settings())
