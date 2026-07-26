"""블로그 이미지 API"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.dependencies import get_blog_admin
from app.dependencies.entities import FirebaseUser
from app.schemas import ImageUploadResponse
from app.services.blog import ImageStorage, get_image_storage
from app.services.blog.images import OversizeError

router = APIRouter(prefix="/images", tags=["blog"])


@router.post("", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile,
    user: FirebaseUser = Depends(get_blog_admin),
    storage: ImageStorage = Depends(get_image_storage),
):
    """이미지 업로드 (관리자)"""
    content = await file.read()
    try:
        filename = storage.save(file.filename or "unnamed", content)
    except OversizeError:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large")
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(e))
    return ImageUploadResponse(url=f"/blog/images/{filename}", filename=filename)


@router.get("/{filename}")
def serve_image(
    filename: str,
    storage: ImageStorage = Depends(get_image_storage),
):
    """이미지 서빙 (공개). Nginx 프록시가 캐싱"""
    path = storage.path_of(filename)
    if path is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Image not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=31536000, immutable"})
