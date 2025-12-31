from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Backend API"
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/backend_api"

    # CORS (localhost는 main.py에서 regex로 모든 포트 허용)
    cors_origins: list[str] = ["https://blog.funq.kr", "https://chat.funq.kr"]

    # Firebase
    firebase_credentials_path: str = "firebase/kid-chat-2ca0f-firebase-adminsdk-fbsvc-094c9dc406.json"

    # Claude CLI
    claude_cli_path: str = "claude"
    claude_timeout_seconds: int = 120
    claude_max_timeout_seconds: int = 300

    # Firebase Test (E2E 테스트용)
    test_firebase_id: str | None = None
    test_firebase_password: str | None = None
    test_firebase_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
