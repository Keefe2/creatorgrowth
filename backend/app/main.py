"""CreatorGrowth API — secure creator growth platform backend.

Runs anywhere: local uvicorn, a container, or a serverless function.
Tables are created at import (idempotent); due scheduled posts are published
opportunistically inside requests (see app/scheduler.py).
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .database import Base, engine
from .middleware import SecurityHeadersMiddleware
from .rate_limit import limiter
from .routers import accounts, analytics, auth, comments, content
from .scheduler import maybe_publish_due

settings = get_settings()

# Idempotent: safe to run on every cold start / import.
Base.metadata.create_all(bind=engine)


def _migrate_is_verified_column() -> None:
    """Add users.is_verified on databases created before email OTP verification.

    Idempotent and dialect-agnostic (SQLite dev + Postgres prod). Any failure
    is logged, never raised, so startup can never crash because of this.
    """
    import logging

    from sqlalchemy import inspect, text

    logger = logging.getLogger(__name__)
    try:
        columns = [c["name"] for c in inspect(engine).get_columns("users")]
        if "is_verified" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE"))
            logger.info("Migrated: added users.is_verified")
    except Exception:
        logger.exception("is_verified migration failed (continuing startup)")


_migrate_is_verified_column()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    # Never expose interactive API docs / schema in production (info disclosure).
    docs_url=None if settings.is_prod else "/docs",
    redoc_url=None if settings.is_prod else "/redoc",
    openapi_url=None if settings.is_prod else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,
)


@app.middleware("http")
async def auto_publish_middleware(request: Request, call_next):
    # Serverless-safe scheduler: publish due posts at most once a minute,
    # piggybacking on real traffic instead of a background thread.
    maybe_publish_due()
    return await call_next(request)


app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(content.router)
app.include_router(analytics.router)
app.include_router(comments.router)


@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
