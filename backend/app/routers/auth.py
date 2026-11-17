"""Authentication router: login and current user profile endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.errors import UnauthorizedError
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserSummary
from app.security import create_access_token, verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and issue JWT access token",
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticate user by email and password.
    Returns JWT bearer token and user summary.
    Employs uniform error messaging on failure to prevent user enumeration attacks.
    """
    user = (
        db.query(User)
        .filter(func.lower(User.email) == func.lower(payload.email.strip()))
        .first()
    )

    # Identical 401 error message for wrong email and wrong password
    if user is None or not verify_password(payload.password, user.password_hash):
        raise UnauthorizedError(
            message="Invalid email or password",
            code="UNAUTHORIZED",
        )

    access_token = create_access_token(user_id=user.id)
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserSummary.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserSummary,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
) -> UserSummary:
    """
    Return currently authenticated user profile.
    Loads user fresh from DB on every call so role modifications apply immediately.
    """
    return UserSummary.model_validate(current_user)
