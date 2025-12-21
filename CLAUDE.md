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
- **Testing**: pytest + httpx

## Project Structure

```
app/
├── main.py          # FastAPI app entry point
├── config.py        # Settings (pydantic-settings)
├── database.py      # SQLAlchemy engine, session, Base
├── models/          # SQLAlchemy models
├── schemas/         # Pydantic request/response schemas
└── routers/         # API route modules
```

## Commands

```bash
# Run dev server
uvicorn app.main:app --reload

# Run tests
pytest tests/ -v

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
- Inherit from `app.database.Base`
- Use type hints for columns

### Pydantic Schemas
- Define in `app/schemas/`
- Separate Create, Update, Response schemas
- Use `model_config = ConfigDict(from_attributes=True)` for ORM compatibility

### Dependencies
- Use `Depends(get_db)` for database sessions
- Create reusable dependencies in `app/dependencies.py` if needed

## Environment Variables

```
DEBUG=false
DATABASE_URL=postgresql://user:pass@localhost:5432/backend_api
CORS_ORIGINS=["http://localhost:3000","http://localhost:3001","https://blog.funq.kr","https://chat.funq.kr"]
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
