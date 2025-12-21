from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Backend API"
    debug: bool = False

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/backend_api"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001", "https://blog.funq.kr", "https://chat.funq.kr"]

    # Firebase
    firebase_credentials_path: str = "firebase/kid-chat-2ca0f-firebase-adminsdk-fbsvc-094c9dc406.json"

    model_config = SettingsConfigDict(env_file=".env")


@lru_cache
def get_settings() -> Settings:
    return Settings()
