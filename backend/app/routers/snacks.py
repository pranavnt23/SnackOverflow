"""Snack inventory API router."""

from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_admin
from app.models import SnackCategory, User
from app.schemas import (
    ConsumeRequest,
    PaginatedSnacksResponse,
    RestockRequest,
    SnackCreate,
    SnackResponse,
    SnackStatus,
    SnackSummaryResponse,
    SnackUpdate,
    VoteStatusResponse,
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


# ===========================================================================
# INVENTORY TRANSACTIONS: CONSUME & RESTOCK
# ===========================================================================

@router.post(
    "/{id}/consume",
    response_model=SnackResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomically consume snack inventory",
)
def consume_snack(
    id: int,
    payload: ConsumeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SnackResponse:
    """
    Atomically decrement snack quantity and log an audit activity within ONE database transaction.
    Returns updated snack details or 409 INSUFFICIENT_STOCK if stock is inadequate.
    """
    return snack_service.consume_snack(
        db=db,
        snack_id=id,
        amount=payload.amount,
        current_user_id=current_user.id,
    )


@router.post(
    "/{id}/restock",
    response_model=SnackResponse,
    status_code=status.HTTP_200_OK,
    summary="Restock snack inventory (Admin only)",
)
def restock_snack(
    id: int,
    payload: RestockRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> SnackResponse:
    """
    Atomically increment snack quantity and record restock activity log (Admin only).
    """
    return snack_service.restock_snack(
        db=db,
        snack_id=id,
        amount=payload.amount,
        current_user_id=current_user.id,
    )


# ===========================================================================
# SNACK VOTING: VOTE & UNVOTE
# ===========================================================================

@router.post(
    "/{id}/vote",
    response_model=VoteStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Vote for a snack",
)
def vote_for_snack(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoteStatusResponse:
    """
    Vote for a snack. Enforced by database composite primary key (user_id, snack_id).
    Returns 409 ALREADY_VOTED if the user has already voted for this snack.
    """
    return snack_service.add_vote(
        db=db,
        snack_id=id,
        current_user_id=current_user.id,
    )


@router.delete(
    "/{id}/vote",
    response_model=VoteStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove vote for a snack",
)
def remove_vote_for_snack(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> VoteStatusResponse:
    """
    Remove an existing vote. Returns 404 VOTE_NOT_FOUND if the user has not voted.
    """
    return snack_service.remove_vote(
        db=db,
        snack_id=id,
        current_user_id=current_user.id,
    )
