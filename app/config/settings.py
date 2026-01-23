from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """
    환경 변수 설정

    우선순위: 시스템 환경변수 > .env 파일 > 기본값
    - venv 실행: .env 파일 사용
    - Docker 실행: docker-compose의 environment가 오버라이드
    """

    # App
    app_name: str = "Backend API"
    debug: bool = False

    # Database (필수 - .env에서 설정)
    database_url: str

    # CORS
    cors_origins: list[str] = []

    # Firebase
    firebase_credentials_path: str = "firebase/kid-chat-2ca0f-firebase-adminsdk-fbsvc-094c9dc406.json"

    # Claude CLI
    claude_cli_path: str = "claude"
    claude_timeout_seconds: int = 120
    claude_max_timeout_seconds: int = 300

    # Firebase Test (E2E 테스트용, 선택)
    test_firebase_id: str | None = None
    test_firebase_password: str | None = None
    test_firebase_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
