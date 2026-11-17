"""Snack inventory API router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.models import SnackCategory, User
from app.schemas import (
    PaginatedSnacksResponse,
    SnackCreate,
    SnackResponse,
    SnackStatus,
    SnackSummaryResponse,
    SnackUpdate,
)
from app.services import snack_service

router = APIRouter(prefix="/snacks", tags=["Snacks"])


@router.get(
    "",
    response_model=PaginatedSnacksResponse,
    status_code=status.HTTP_200_OK,
    summary="List snacks with filtering, search, and pagination",
)
def list_snacks(
    category: Optional[SnackCategory] = Query(default=None, description="Filter by category"),
    status: Optional[SnackStatus] = Query(default=None, description="Filter by derived stock status"),
    search: Optional[str] = Query(default=None, description="Case-insensitive partial name match"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=50, description="Items per page (max 50)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedSnacksResponse:
    """
    Retrieve paginated snacks with SQL-evaluated status, vote counts, and user vote status.
    All search, filtering, and pagination are executed entirely in PostgreSQL.
    """
    return snack_service.get_snacks(
        db=db,
        current_user_id=current_user.id,
        category=category,
        status=status,
        search=search,
        page=page,
        page_size=page_size,
    )


# IMPORTANT: /summary MUST be declared BEFORE /{id} so "summary" is not interpreted as an integer ID
@router.get(
    "/summary",
    response_model=SnackSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pantry stock summary counts and snack of the week",
)
def get_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SnackSummaryResponse:
    """
    Return pantry stock counts calculated via a single grouped SQL query
    alongside the Snack of the Week (highest votes, ties broken by name).
    """
    return snack_service.get_snacks_summary(db=db, current_user_id=current_user.id)


@router.get(
    "/{id}",
    response_model=SnackResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single snack by ID",
)
def get_snack(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SnackResponse:
    """Fetch single snack by ID. Returns 404 NOT_FOUND if it does not exist."""
    return snack_service.get_snack_by_id(db=db, snack_id=id, current_user_id=current_user.id)


@router.post(
    "",
    response_model=SnackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new pantry snack (Admin only)",
)
def create_snack(
    payload: SnackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SnackResponse:
    """
    Create a new pantry snack item.
    Enforces name uniqueness and returns 409 DUPLICATE_NAME on conflict.
    """
    return snack_service.create_snack(db=db, payload=payload, current_user_id=current_user.id)


@router.patch(
    "/{id}",
    response_model=SnackResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update snack metadata (Admin only)",
)
def update_snack(
    id: int,
    payload: SnackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SnackResponse:
    """
    Partially update snack name, category, or low stock threshold.
    Quantity cannot be modified via PATCH (only via atomic restock/consume transactions).
    """
    return snack_service.update_snack(db=db, snack_id=id, payload=payload, current_user_id=current_user.id)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a snack (Admin only)",
)
def delete_snack(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> None:
    """
    Delete a snack from inventory.
    Votes cascade and activities remain intact with snack_id set to NULL.
    """
    snack_service.delete_snack(db=db, snack_id=id)
