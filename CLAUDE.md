# Backend API - Claude Code Instructions

## Project Overview

FastAPI backend API for `api.funq.kr`. PostgreSQL database with SQLAlchemy ORM and Alembic migrations.

**주요 기능**:
- AI 채팅 (Claude API)
- 가족 캘린더 (일정 관리, 반복 일정, 카테고리)
- Firebase 인증

## Tech Stack

- **Python**: 3.12
- **Framework**: FastAPI 0.115.6
- **Server**: Uvicorn 0.34.0
- **ORM**: SQLAlchemy 2.0.36
- **Database**: PostgreSQL (psycopg2-binary)
- **Migrations**: Alembic 1.14.0
- **Config**: pydantic-settings 2.7.0
- **Recurrence**: python-dateutil 2.9.0 (반복 일정 RRULE 처리)
- **Auth**: firebase-admin 6.4.0
- **Testing**: pytest + pytest-cov + pytest-asyncio + httpx

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
│   ├── claude/          # Claude AI 서비스
│   │   ├── __init__.py
│   │   ├── protocol.py  # AIServiceProtocol
│   │   ├── service.py   # ClaudeService 구현
│   │   ├── personas.py  # AI 페르소나 정의
│   │   └── dependencies.py # get_claude_service
│   └── calendar/        # 캘린더 서비스
│       ├── __init__.py
│       ├── protocol.py  # 서비스 프로토콜 정의
│       ├── service.py   # MemberService, CategoryService, EventService
│       ├── recurrence.py # RRULE 파싱 및 반복 일정 확장
│       └── dependencies.py # get_*_service 의존성
├── models/              # SQLAlchemy models
│   ├── __init__.py
│   └── calendar.py      # FamilyMember, Category, Event, RecurrenceException
├── schemas/             # Pydantic request/response schemas
│   ├── __init__.py
│   ├── ai.py            # AI 채팅 스키마
│   └── calendar.py      # 캘린더 관련 스키마
└── routers/             # API route modules
    ├── __init__.py
    ├── health.py        # 헬스체크 (/health)
    ├── auth.py          # 인증 (/auth)
    ├── ai.py            # AI 채팅 (/ai)
    └── calendar/        # 캘린더 라우터 (/calendar)
        ├── __init__.py  # 라우터 통합
        ├── auth.py      # 캘린더 인증 (/calendar/auth)
        ├── members.py   # 가족 구성원 (/calendar/members)
        ├── categories.py # 카테고리 (/calendar/categories)
        └── events.py    # 일정 (/calendar/events)

tests/
├── conftest.py          # 공통 pytest fixtures
├── fakes/               # Fake 구현체 (TDD용)
│   ├── __init__.py
│   ├── fake_auth.py
│   ├── fake_claude.py
│   ├── fake_database.py
│   └── fake_calendar.py # 캘린더 Fake 서비스
├── unit/                # 단위 테스트
│   ├── test_dependencies.py
│   ├── test_external.py
│   └── services/
│       ├── test_claude_service.py
│       ├── test_personas.py
│       └── test_recurrence.py  # 반복 일정 로직 테스트
├── integration/         # 통합 테스트 (DI 사용)
│   ├── test_health.py
│   ├── test_auth.py
│   ├── test_ai.py
│   ├── test_calendar_auth.py
│   ├── test_members.py
│   ├── test_categories.py
│   └── test_events.py
└── e2e/                 # E2E 테스트 (실제 서비스)
    ├── test_firebase.py
    └── test_claude_service.py
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

## API Endpoints

### Health
- `GET /health` - 서버 상태 확인

### Auth
- `POST /auth/verify` - Firebase 토큰 검증

### AI
- `POST /ai/chat` - Claude AI 채팅

### Calendar
- `POST /calendar/auth/verify` - Firebase 인증 및 가족 구성원 연결
- `GET /calendar/members` - 가족 구성원 목록
- `POST /calendar/members` - 가족 구성원 생성
- `PUT /calendar/members/{id}` - 가족 구성원 수정
- `DELETE /calendar/members/{id}` - 가족 구성원 삭제
- `GET /calendar/categories` - 카테고리 목록
- `POST /calendar/categories` - 카테고리 생성
- `PUT /calendar/categories/{id}` - 카테고리 수정
- `DELETE /calendar/categories/{id}` - 카테고리 삭제
- `GET /calendar/events` - 일정 조회 (start_date, end_date 쿼리)
- `POST /calendar/events` - 일정 생성 (반복 일정 지원)
- `PUT /calendar/events/{id}` - 일정 수정
- `DELETE /calendar/events/{id}` - 일정 삭제

## Calendar Models

### FamilyMember (가족 구성원)
- `id`: UUID (PK)
- `firebase_uid`: Firebase UID (nullable, unique)
- `email`: 이메일 (unique)
- `display_name`: 표시 이름
- `color`: 색상 (#RRGGBB)
- `is_registered`: 가입 여부

### Category (카테고리)
- `id`: UUID (PK)
- `name`: 카테고리명
- `color`: 색상 (#RRGGBB)
- `icon`: 아이콘 (optional)

### Event (일정)
- `id`: UUID (PK)
- `title`: 제목
- `description`: 설명 (optional)
- `start_time`, `end_time`: 시작/종료 시간
- `all_day`: 종일 여부
- `category_id`: 카테고리 FK
- `created_by`: 생성자 FK (FamilyMember)
- `recurrence_rule`: RRULE 문자열 (optional)
- `recurrence_start`, `recurrence_end`: 반복 기간

### RecurrenceException (반복 예외)
- `id`: UUID (PK)
- `event_id`: Event FK
- `original_date`: 원래 날짜
- `is_deleted`: 삭제 여부
- `modified_event`: 수정된 이벤트 데이터 (JSONB)

## Environment Variables

```
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost:5432/backend_api
CORS_ORIGINS=["https://blog.funq.kr","https://chat.funq.kr","https://calendar.funq.kr"]
GOOGLE_APPLICATION_CREDENTIALS=path/to/firebase-credentials.json
ANTHROPIC_API_KEY=your-api-key
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
