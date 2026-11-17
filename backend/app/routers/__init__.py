"""API Routers package."""

from app.routers.auth import router as auth_router
from app.routers.snacks import router as snacks_router

__all__ = ["auth_router", "snacks_router"]
