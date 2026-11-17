"""Security utilities: password hashing with bcrypt and JWT handling with PyJWT."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import bcrypt
import jwt

from app.config import get_settings
from app.errors import UnauthorizedError

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt directly."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed HS256 JWT with sub=str(user_id) and expiration."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta if expires_delta else timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    )
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int:
    """
    Decode and validate an HS256 JWT token.
    Returns the integer user_id from the 'sub' claim.
    Raises UnauthorizedError if token is expired, corrupted, or missing 'sub'.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if not sub:
            raise UnauthorizedError(message="Token missing subject identifier", code="UNAUTHORIZED")
        return int(sub)
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError(message="Authentication token has expired", code="UNAUTHORIZED")
    except (jwt.PyJWTError, ValueError):
        raise UnauthorizedError(message="Invalid authentication token", code="UNAUTHORIZED")
