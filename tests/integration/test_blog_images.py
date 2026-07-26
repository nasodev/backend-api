"""Blog Images API 통합 테스트"""

import io

import pytest

from app.services.blog.images import ImageStorage
from app.services.blog.dependencies import get_image_storage
from app.main import app
from fastapi.testclient import TestClient
from app.dependencies.blog_admin import get_blog_admin


@pytest.fixture
def image_storage(tmp_path):
    """임시 디렉터리 기반 이미지 스토리지"""
    return ImageStorage(base_dir=tmp_path)


@pytest.fixture
def client_with_image_storage(image_storage, fake_user):
    app.dependency_overrides[get_image_storage] = lambda: image_storage
    app.dependency_overrides[get_blog_admin] = lambda: fake_user
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"0" * 100


class TestImageUpload:
    def test_upload_requires_auth(self, client):
        response = client.post("/blog/images")
        assert response.status_code == 403

    def test_upload_success(self, client_with_image_storage):
        response = client_with_image_storage.post(
            "/blog/images",
            files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["filename"].endswith(".png")
        assert body["url"] == f"/blog/images/{body['filename']}"

    def test_upload_rejects_bad_extension(self, client_with_image_storage):
        response = client_with_image_storage.post(
            "/blog/images",
            files={"file": ("script.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert response.status_code == 400

    def test_upload_rejects_oversize(self, client_with_image_storage):
        big = b"0" * (10 * 1024 * 1024 + 1)
        response = client_with_image_storage.post(
            "/blog/images",
            files={"file": ("big.png", io.BytesIO(big), "image/png")},
        )
        assert response.status_code == 413

    def test_serve_uploaded_image(self, client_with_image_storage):
        upload = client_with_image_storage.post(
            "/blog/images",
            files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
        ).json()
        response = client_with_image_storage.get(upload["url"])
        assert response.status_code == 200
        assert response.content == PNG_BYTES

    def test_serve_missing_404(self, client_with_image_storage):
        response = client_with_image_storage.get("/blog/images/nope.png")
        assert response.status_code == 404

    def test_serve_path_traversal_blocked(self, client_with_image_storage):
        response = client_with_image_storage.get("/blog/images/..%2F..%2Fetc%2Fpasswd")
        assert response.status_code in (404, 400)
