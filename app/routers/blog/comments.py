"""Native public comment and admin moderation endpoints."""
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.exception_handlers import http_exception_handler
from starlette.exceptions import HTTPException

from app.dependencies.blog_admin import get_blog_admin
from app.dependencies.blog_comments import get_comment_service, optional_comment_user
from app.schemas.blog_comments import Comment, CommentCreate, CommentPage, CommentUpdate, GithubImportRequest, GithubImportResult, PasswordInput
from app.services.blog.comment_security import client_address


class PrivateCommentRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def protected(request):
            try:
                response = await handler(request)
            except RequestValidationError as exc:
                # Pydantic's SecretStr/hide_input_in_errors does not remove FastAPI's
                # error input dictionaries (including whole model/invalid type input).
                response = JSONResponse(status_code=422, content={'detail': [
                    {'loc': error['loc'], 'msg': error['msg'], 'type': error['type']}
                    for error in exc.errors()
                ]})
            except HTTPException as exc:
                response = await http_exception_handler(request, exc)
            response.headers['Cache-Control'] = 'private, no-store'
            response.headers['Vary'] = 'Authorization'
            return response
        return protected


router = APIRouter(tags=['blog comments'], route_class=PrivateCommentRoute)


def address(request, service):
    return client_address(request, service.settings.blog_comment_trusted_proxy_networks)


@router.get('/posts/{slug}/comments', response_model=CommentPage)
def list_comments(slug: str, limit: int = Query(20, ge=1, le=50), cursor: str | None = None,
                  user=Depends(optional_comment_user), service=Depends(get_comment_service)):
    return service.list(slug, user, limit, cursor)


@router.post('/posts/{slug}/comments', response_model=Comment, status_code=201)
def create_comment(slug: str, data: CommentCreate, request: Request,
                   user=Depends(optional_comment_user), service=Depends(get_comment_service)):
    return service.create(slug, data, user, address(request, service))


@router.patch('/posts/{slug}/comments/{identifier}', response_model=Comment)
def update_comment(slug: str, identifier: UUID, data: CommentUpdate, request: Request,
                   user=Depends(optional_comment_user), service=Depends(get_comment_service)):
    return service.update(slug, identifier, data, user, address(request, service))


@router.delete('/posts/{slug}/comments/{identifier}', status_code=204)
def delete_comment(slug: str, identifier: UUID, request: Request, data: PasswordInput | None = Body(None),
                   user=Depends(optional_comment_user), service=Depends(get_comment_service)):
    service.delete(identifier, slug, user, data.password if data else None, address(request, service))


@router.get('/admin/comments', response_model=CommentPage)
def admin_comments(limit: int = Query(20, ge=1, le=50), cursor: str | None = None,
                   user=Depends(get_blog_admin), service=Depends(get_comment_service)):
    return service.list(user=user, limit=limit, cursor=cursor)


@router.delete('/admin/comments/{identifier}', status_code=204)
def admin_delete_comment(identifier: UUID, user=Depends(get_blog_admin), service=Depends(get_comment_service)):
    service.delete(identifier, user=user)


@router.post('/admin/comments/import-github', response_model=GithubImportResult)
def import_github(data: GithubImportRequest, user=Depends(get_blog_admin), service=Depends(get_comment_service)):
    return service.import_github(data)
