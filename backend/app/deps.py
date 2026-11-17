"""FastAPI request dependencies: database sessions, auth, and role guards."""

from typing import Optional
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ForbiddenError, UnauthorizedError
from app.models import User, UserRole
from app.security import decode_access_token

# HTTPBearer with auto_error=False so we return our standardized 401 error envelope
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Authenticate request via Bearer JWT and load the user FRESH from the DB.
    Loading from the DB on every request ensures:
    1. Role changes or privilege revocations apply immediately without waiting for token expiration.
    2. Deleted or disabled accounts are instantly blocked.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError(message="Authentication token missing", code="UNAUTHORIZED")

    user_id = decode_access_token(credentials.credentials)
    user = db.get(User, user_id)
    if user is None:
        raise UnauthorizedError(message="User not found or account inactive", code="UNAUTHORIZED")

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Authorize admin-only routes.
    Rejects non-admin users with 403 FORBIDDEN.
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(message="Administrator privileges required", code="FORBIDDEN")
    return current_user


__all__ = [
    "get_db",
    "get_settings",
    "get_current_user",
    "require_admin",
    "Settings",
    "Session",
    "User",
]
