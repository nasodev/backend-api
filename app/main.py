from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, auth, ai, members, categories, events

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=r"^http://localhost(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(ai.router)
app.include_router(members.router)
app.include_router(categories.router)
app.include_router(events.router)


@app.get("/")
def root():
    return {"message": "Backend API is running"}
