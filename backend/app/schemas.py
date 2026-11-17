"""Pydantic schemas for validation and API serialization."""

import enum
from datetime import datetime
from typing import List, Optional
import email_validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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
# User & Authentication Schemas
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


class LoginRequest(BaseModel):
    """Authentication request credentials."""
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class TokenResponse(BaseModel):
    """Login response with JWT bearer token and user summary."""
    access_token: str
    token_type: str = "bearer"
    user: UserSummary


# ---------------------------------------------------------------------------
# Snack Status & Schemas
# ---------------------------------------------------------------------------
class SnackStatus(str, enum.Enum):
    """Runtime derived snack inventory status."""
    STOCKED = "stocked"
    RUNNING_LOW = "running_low"
    GONE = "gone"


class SnackBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    category: SnackCategory
    low_stock_threshold: int = Field(default=5, ge=0)

    @field_validator("name")
    @classmethod
    def validate_and_strip_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Snack name cannot be empty or whitespace only")
        if len(trimmed) > 100:
            raise ValueError("Snack name cannot exceed 100 characters")
        return trimmed


class SnackCreate(SnackBase):
    quantity: int = Field(default=0, ge=0)


class SnackUpdate(BaseModel):
    """Payload for partial snack update by admin. Quantity is forbidden here."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[SnackCategory] = None
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid")

    @field_validator("name")
    @classmethod
    def validate_and_strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            trimmed = v.strip()
            if not trimmed:
                raise ValueError("Snack name cannot be empty or whitespace only")
            if len(trimmed) > 100:
                raise ValueError("Snack name cannot exceed 100 characters")
            return trimmed
        return v


class SnackResponse(BaseModel):
    id: int
    name: str
    category: SnackCategory
    quantity: int = Field(..., ge=0)
    low_stock_threshold: int = Field(..., ge=0)
    status: SnackStatus
    vote_count: int = 0
    has_voted: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSnacksResponse(BaseModel):
    """Paginated list of snacks."""
    items: List[SnackResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class SnackSummaryResponse(BaseModel):
    """Aggregated pantry stock summary and snack of the week."""
    stocked: int
    running_low: int
    gone: int
    total: int
    snack_of_the_week: Optional[SnackResponse] = None


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


class VoteStatusResponse(BaseModel):
    """Real-time vote status response for a snack."""
    snack_id: int
    vote_count: int
    has_voted: bool


# ---------------------------------------------------------------------------
# Stock Action Schemas
# ---------------------------------------------------------------------------
class ConsumeRequest(BaseModel):
    """Payload for consuming pantry stock."""
    amount: int = Field(..., ge=1, le=100, description="Packets to consume (1..100)")


class RestockRequest(BaseModel):
    """Payload for restocking pantry inventory."""
    amount: int = Field(..., ge=1, le=1000, description="Packets to restock (1..1000)")


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
