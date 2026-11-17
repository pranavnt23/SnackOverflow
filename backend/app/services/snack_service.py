"""Snack service: business logic, query composition, and derived status calculations."""

from typing import List, Optional
from sqlalchemy import and_, case, func, literal, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Snack, SnackCategory, Vote
from app.schemas import (
    PaginatedSnacksResponse,
    SnackCreate,
    SnackResponse,
    SnackStatus,
    SnackSummaryResponse,
    SnackUpdate,
)


def get_snack_status_sql():
    """
    SQL CASE expression building the derived snack inventory status:
    - 'gone' when quantity = 0
    - 'running_low' when quantity BETWEEN 1 AND low_stock_threshold
    - else 'stocked'
    """
    return case(
        (Snack.quantity == 0, "gone"),
        (Snack.quantity.between(1, Snack.low_stock_threshold), "running_low"),
        else_="stocked",
    ).label("status")


def escape_like_string(value: str) -> str:
    """Escape SQL LIKE/ILIKE wildcards: backslash, percent, and underscore."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_snack_query(current_user_id: Optional[int] = None):
    """
    Construct base query fetching Snack with derived status, total vote count,
    and whether the current user has voted, in a single SQL roundtrip (avoiding N+1 queries).
    """
    status_expr = get_snack_status_sql()

    # Correlated scalar subquery for total votes per snack
    vote_count_subq = (
        select(func.count(Vote.user_id))
        .where(Vote.snack_id == Snack.id)
        .scalar_subquery()
        .label("vote_count")
    )

    # Correlated EXISTS subquery for current user's vote
    if current_user_id is not None:
        has_voted_subq = (
            select(literal(True))
            .where(and_(Vote.snack_id == Snack.id, Vote.user_id == current_user_id))
            .exists()
            .label("has_voted")
        )
    else:
        has_voted_subq = literal(False).label("has_voted")

    return select(Snack, status_expr, vote_count_subq, has_voted_subq)


def row_to_snack_response(snack: Snack, status_val: str, vote_count: int, has_voted: bool) -> SnackResponse:
    """Map SQL query result tuple to validated SnackResponse schema."""
    return SnackResponse(
        id=snack.id,
        name=snack.name,
        category=snack.category,
        quantity=snack.quantity,
        low_stock_threshold=snack.low_stock_threshold,
        status=SnackStatus(status_val),
        vote_count=vote_count,
        has_voted=has_voted,
        created_at=snack.created_at,
        updated_at=snack.updated_at,
    )


def get_snacks(
    db: Session,
    current_user_id: int,
    category: Optional[SnackCategory] = None,
    status: Optional[SnackStatus] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> PaginatedSnacksResponse:
    """
    Query snacks with SQL filtering, sorting, and pagination.
    Avoids in-memory filtering for production scalability.
    """
    query = build_snack_query(current_user_id)
    count_query = select(func.count(Snack.id))

    # Apply filters
    if category is not None:
        query = query.where(Snack.category == category)
        count_query = count_query.where(Snack.category == category)

    if status is not None:
        status_filter = get_snack_status_sql() == status.value
        query = query.where(status_filter)
        count_query = count_query.where(status_filter)

    if search and search.strip():
        escaped = escape_like_string(search.strip())
        search_filter = Snack.name.ilike(f"%{escaped}%", escape="\\")
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Compute total matching items
    total = db.scalar(count_query) or 0
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0

    # Paginate and order by name
    query = query.order_by(Snack.name.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = db.execute(query).all()

    items = [
        row_to_snack_response(snack, status_val, vote_count, has_voted)
        for snack, status_val, vote_count, has_voted in rows
    ]

    return PaginatedSnacksResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_snacks_summary(db: Session, current_user_id: int) -> SnackSummaryResponse:
    """
    Calculate summary inventory counts via a single grouped SQL query,
    and find the Snack of the Week (most votes; ties broken by name).
    """
    status_expr = get_snack_status_sql()
    grouped_counts_query = (
        select(status_expr, func.count(Snack.id))
        .select_from(Snack)
        .group_by(status_expr)
    )
    rows = db.execute(grouped_counts_query).all()

    counts = {"stocked": 0, "running_low": 0, "gone": 0}
    for status_val, count in rows:
        counts[status_val] = count

    total = sum(counts.values())

    # Snack of the Week: highest vote count, ties broken by name ascending, null if no votes
    sotw_query = (
        select(Vote.snack_id)
        .join(Snack, Snack.id == Vote.snack_id)
        .group_by(Vote.snack_id, Snack.name)
        .order_by(func.count(Vote.user_id).desc(), Snack.name.asc())
        .limit(1)
    )
    sotw_id = db.scalar(sotw_query)

    snack_of_the_week = get_snack_by_id(db, sotw_id, current_user_id) if sotw_id is not None else None

    return SnackSummaryResponse(
        stocked=counts["stocked"],
        running_low=counts["running_low"],
        gone=counts["gone"],
        total=total,
        snack_of_the_week=snack_of_the_week,
    )


def get_snack_by_id(db: Session, snack_id: int, current_user_id: int) -> SnackResponse:
    """Retrieve a single snack by primary key with derived status and vote statistics."""
    query = build_snack_query(current_user_id).where(Snack.id == snack_id)
    row = db.execute(query).first()
    if not row:
        raise NotFoundError(message=f"Snack with id {snack_id} not found", code="NOT_FOUND")

    snack, status_val, vote_count, has_voted = row
    return row_to_snack_response(snack, status_val, vote_count, has_voted)


def create_snack(db: Session, payload: SnackCreate, current_user_id: int) -> SnackResponse:
    """
    Create a new pantry snack (admin only).
    Enforces uniqueness on snack name and catches IntegrityError for 409 DUPLICATE_NAME.
    """
    new_snack = Snack(
        name=payload.name,
        category=payload.category,
        quantity=payload.quantity,
        low_stock_threshold=payload.low_stock_threshold,
    )
    db.add(new_snack)
    try:
        db.commit()
        db.refresh(new_snack)
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            message=f"A snack with name '{payload.name}' already exists",
            code="DUPLICATE_NAME",
        )

    return get_snack_by_id(db, new_snack.id, current_user_id)


def update_snack(db: Session, snack_id: int, payload: SnackUpdate, current_user_id: int) -> SnackResponse:
    """
    Partially update a snack's metadata (admin only).
    Quantity updates are forbidden here (only modified via atomic restock/consume).
    """
    snack = db.get(Snack, snack_id)
    if not snack:
        raise NotFoundError(message=f"Snack with id {snack_id} not found", code="NOT_FOUND")

    if payload.name is not None:
        snack.name = payload.name
    if payload.category is not None:
        snack.category = payload.category
    if payload.low_stock_threshold is not None:
        snack.low_stock_threshold = payload.low_stock_threshold

    try:
        db.commit()
        db.refresh(snack)
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            message=f"A snack with name '{payload.name}' already exists",
            code="DUPLICATE_NAME",
        )

    return get_snack_by_id(db, snack.id, current_user_id)


def delete_snack(db: Session, snack_id: int) -> None:
    """
    Delete a snack from the catalogue (admin only).
    Votes cascade and activities are retained with snack_id set to NULL.
    """
    snack = db.get(Snack, snack_id)
    if not snack:
        raise NotFoundError(message=f"Snack with id {snack_id} not found", code="NOT_FOUND")

    db.delete(snack)
    db.commit()
