"""블로그 이미지 파일 스토리지"""

import uuid
from pathlib import Path

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10MB


class ImageStorage:
    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, original_filename: str, content: bytes) -> str:
        """검증 후 UUID 파일명으로 저장, 저장된 파일명 반환.

        Raises:
            ValueError: 허용되지 않는 확장자
            OversizeError: 크기 초과
        """
        ext = Path(original_filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Extension not allowed: {ext}")
        if len(content) > MAX_IMAGE_BYTES:
            raise OversizeError(f"File exceeds {MAX_IMAGE_BYTES} bytes")

        filename = f"{uuid.uuid4()}{ext}"
        (self.base_dir / filename).write_bytes(content)
        return filename

    def path_of(self, filename: str) -> Path | None:
        """서빙용 경로 반환. 없거나 base_dir 탈출 시 None"""
        candidate = (self.base_dir / filename).resolve()
        if not candidate.is_file():
            return None
        if self.base_dir.resolve() not in candidate.parents:
            return None
        return candidate


class OversizeError(Exception):
    pass
