"""블로그 서비스 의존성 주입"""

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import get_settings
from app.external.database import get_db
from app.services.blog.images import ImageStorage
from app.services.blog.protocol import BlogServiceProtocol
from app.services.blog.service import BlogService


def get_blog_service(db: Session = Depends(get_db)) -> BlogServiceProtocol:
    """테스트에서 override: app.dependency_overrides[get_blog_service] = lambda: FakeBlogService()"""
    return BlogService(db)


def get_image_storage() -> ImageStorage:
    """테스트에서 override: app.dependency_overrides[get_image_storage] = lambda: ImageStorage(tmp)"""
    settings = get_settings()
    return ImageStorage(base_dir=settings.blog_image_dir)
