"""FastAPI entrypoint for Snack Overflow backend application."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import engine, get_db
from app.errors import DatabaseError, register_error_handlers
from app.routers import auth_router, snacks_router
from app.schemas import HealthResponse

logger = logging.getLogger("snack_overflow")
logging.basicConfig(level=logging.INFO)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context for startup and shutdown hooks."""
    logger.info("Snack Overflow backend initializing...")
    yield
    logger.info("Snack Overflow backend shutting down, disposing engine...")
    engine.dispose()


app = FastAPI(
    title="Snack Overflow API",
    description="Office pantry tracker and stock management system.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register uniform {"error": {"code": "...", "message": "..."}} error handlers
register_error_handlers(app)

# Include API routers
app.include_router(auth_router)
app.include_router(snacks_router)


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check with DB connectivity ping",
)
def health_check(db: Session = Depends(get_db)) -> HealthResponse:
    """
    Health check endpoint.
    Verifies that the API server and the underlying PostgreSQL database are operational
    by executing a lightweight `SELECT 1` ping.
    """
    try:
        db.execute(text("SELECT 1"))
        return HealthResponse(status="ok", database="connected")
    except Exception as exc:
        logger.error(f"Database health ping failed: {exc}", exc_info=True)
        raise DatabaseError(message=f"Database connectivity check failed: {str(exc)}")
