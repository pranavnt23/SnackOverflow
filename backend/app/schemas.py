"""Pydantic schemas for validation and API serialization."""

from datetime import datetime
from typing import Optional
import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field, computed_field

# Allow '.local' domain for development / demo emails (e.g. admin@snack.local)
if hasattr(email_validator, "SPECIAL_USE_DOMAIN_NAMES") and "local" in email_validator.SPECIAL_USE_DOMAIN_NAMES:
    email_validator.SPECIAL_USE_DOMAIN_NAMES.remove("local")

from app.models import ActivityAction, SnackCategory, UserRole


# ---------------------------------------------------------------------------
# Standard Error Envelope Schema
# ---------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    """Inner error payload containing code, human-readable message, and optional field details."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error description")
    details: Optional[list] = Field(default=None, description="Detailed field-level validation errors")


class ErrorResponse(BaseModel):
    """Global standardized API error response envelope."""
    error: ErrorDetail


# ---------------------------------------------------------------------------
# Health Check Schema
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(default="ok", json_schema_extra={"example": "ok"})
    database: str = Field(default="connected", json_schema_extra={"example": "connected"})


# ---------------------------------------------------------------------------
# User Schemas
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.MEMBER


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserSummary(BaseModel):
    """Safe user profile excluding credentials."""
    id: int
    name: str
    email: str
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Snack Schemas (Status is Derived)
# ---------------------------------------------------------------------------
class SnackBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    category: SnackCategory
    low_stock_threshold: int = Field(default=5, ge=0)


class SnackCreate(SnackBase):
    quantity: int = Field(default=0, ge=0)


class SnackResponse(SnackBase):
    id: int
    quantity: int = Field(..., ge=0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @computed_field  # type: ignore[misc]
    @property
    def status(self) -> str:
        """
        Derived snack inventory status:
        - 'stocked': quantity > low_stock_threshold
        - 'running_low': 1 <= quantity <= low_stock_threshold
        - 'gone': quantity == 0
        """
        if self.quantity > self.low_stock_threshold:
            return "stocked"
        elif self.quantity > 0:
            return "running_low"
        return "gone"


# ---------------------------------------------------------------------------
# Vote Schemas
# ---------------------------------------------------------------------------
class VoteCreate(BaseModel):
    snack_id: int


class VoteResponse(BaseModel):
    user_id: int
    snack_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Activity Audit Schemas
# ---------------------------------------------------------------------------
class ActivityResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    snack_id: Optional[int] = None
    snack_name: str
    action: ActivityAction
    amount: int
    quantity_after: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
