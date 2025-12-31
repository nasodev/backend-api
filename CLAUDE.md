# Backend API - Claude Code Instructions

## Project Overview

FastAPI backend API for `api.funq.kr`. PostgreSQL database with SQLAlchemy ORM and Alembic migrations.

## Tech Stack

- **Python**: 3.12
- **Framework**: FastAPI 0.115.6
- **Server**: Uvicorn 0.34.0
- **ORM**: SQLAlchemy 2.0.36
- **Database**: PostgreSQL (psycopg2-binary)
- **Migrations**: Alembic 1.14.0
- **Config**: pydantic-settings 2.7.0
- **Testing**: pytest + pytest-cov + pytest-asyncio

## Project Structure

```
app/
├── main.py              # FastAPI app entry point
├── config/              # 설정 모듈
│   ├── __init__.py
│   └── settings.py      # Settings (pydantic-settings)
├── external/            # 외부 연동 (DB, Firebase)
│   ├── __init__.py
│   ├── database.py      # SQLAlchemy engine, session, Base
│   └── firebase.py      # Firebase Admin SDK
├── dependencies/        # FastAPI 의존성 주입
│   ├── __init__.py
│   ├── protocol.py      # AuthServiceProtocol
│   ├── entities.py      # FirebaseUser 엔티티
│   ├── auth.py          # get_current_user 의존성
│   └── token_verifier.py # 토큰 검증 의존성
├── services/            # 비즈니스 로직
│   └── claude/          # Claude AI 서비스
│       ├── __init__.py
│       ├── protocol.py  # AIServiceProtocol
│       ├── service.py   # ClaudeService 구현
│       ├── personas.py  # AI 페르소나 정의
│       └── dependencies.py # get_claude_service
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic request/response schemas
└── routers/             # API route modules

tests/
├── conftest.py          # 공통 pytest fixtures
├── fakes/               # Fake 구현체 (TDD용)
│   ├── fake_auth.py
│   ├── fake_claude.py
│   └── fake_database.py
├── unit/                # 단위 테스트
├── integration/         # 통합 테스트 (DI 사용)
└── e2e/                 # E2E 테스트 (실제 서비스)
```

## Commands

```bash
# Run dev server
uvicorn app.main:app --reload

# Run tests (E2E 제외, 기본)
pytest

# Run all tests (E2E 포함)
pytest -m ""

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run E2E tests only
pytest -m e2e

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Conventions

### API Routes
- Place routers in `app/routers/` with descriptive names
- Use `APIRouter` with `prefix` and `tags`
- Include router in `app/main.py` via `app.include_router()`

### Database Models
- Define in `app/models/` and import in `app/models/__init__.py`
- Inherit from `app.external.Base`
- Use type hints for columns

### Pydantic Schemas
- Define in `app/schemas/`
- Separate Create, Update, Response schemas
- Use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility

### Dependencies (TDD 패턴)
- `app/dependencies/` - 인증 관련 의존성
- `app/services/*/dependencies.py` - 서비스별 의존성
- Protocol 기반 인터페이스로 Fake 주입 가능
- 테스트에서 `app.dependency_overrides`로 Fake 교체

### Testing
- `tests/fakes/` - Fake 구현체 (FakeAuthService, FakeClaudeService 등)
- `tests/unit/` - 단위 테스트 (외부 의존성 없음)
- `tests/integration/` - 통합 테스트 (Fake DI 사용)
- `tests/e2e/` - E2E 테스트 (실제 서비스, `@pytest.mark.e2e`)

## Environment Variables

```
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost:5432/backend_api
CORS_ORIGINS=["https://blog.funq.kr","https://chat.funq.kr"]
```

## Deployment

- **Server**: `/home/funq/dev/backend-api`
- **Service**: `backend-api.service` (systemd)
- **Proxy**: Nginx → port 8000
- **CI/CD**: GitHub Actions on push to `main`

## Testing Guidelines

- Test files in `tests/` directory
- Use `TestClient` from `fastapi.testclient`
- Name test files `test_*.py`
- Run `pytest tests/ -v` before committing
