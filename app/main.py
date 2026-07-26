from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import health, auth, ai, ccusage
from app.routers.calendar import router as calendar_router
from app.routers.blog import router as blog_router
from app.exception_handlers import register_exception_handlers

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Exception handlers
register_exception_handlers(app)

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
app.include_router(calendar_router)
app.include_router(ccusage.router)
app.include_router(blog_router)


@app.get("/")
def root():
    return {"message": "Backend API is running"}
