"""Test suite for database models, constraints, and relational integrity."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from app.config import get_settings
from app.models import Activity, ActivityAction, Snack, SnackCategory, User, UserRole, Vote

settings = get_settings()
engine = create_engine(settings.sqlalchemy_database_url)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db_session():
    """Provide a transactional database session rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_snack_quantity_check_constraint(db_session):
    """Verify DB rejects negative quantity via CHECK constraint."""
    snack = Snack(
        name="Negative Quantity Snack",
        category=SnackCategory.SWEET,
        quantity=-1,
        low_stock_threshold=5,
    )
    db_session.add(snack)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_snack_threshold_check_constraint(db_session):
    """Verify DB rejects negative low_stock_threshold via CHECK constraint."""
    snack = Snack(
        name="Negative Threshold Snack",
        category=SnackCategory.SWEET,
        quantity=10,
        low_stock_threshold=-2,
    )
    db_session.add(snack)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_activity_amount_check_constraint(db_session):
    """Verify DB rejects activity amount <= 0 via CHECK constraint."""
    user = User(
        name="Alice Tester",
        email="alice.constraint.test@example.com",
        password_hash="hashed_pw_dummy",
        role=UserRole.MEMBER,
    )
    db_session.add(user)
    db_session.flush()

    activity = Activity(
        user_id=user.id,
        snack_id=None,
        snack_name="Test Pretzel",
        action=ActivityAction.CONSUMED,
        amount=0,  # Invalid: amount must be > 0
        quantity_after=5,
    )
    db_session.add(activity)
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_vote_composite_primary_key_uniqueness(db_session):
    """Verify composite PK (user_id, snack_id) prevents duplicate votes."""
    user = User(
        name="Bob Voter",
        email="bob.voter.test@example.com",
        password_hash="hashed_pw_dummy",
        role=UserRole.MEMBER,
    )
    snack = Snack(
        name="Almond Butter Cups",
        category=SnackCategory.SWEET,
        quantity=20,
        low_stock_threshold=5,
    )
    db_session.add_all([user, snack])
    db_session.flush()

    vote1 = Vote(user_id=user.id, snack_id=snack.id)
    db_session.add(vote1)
    db_session.flush()

    vote2 = Vote(user_id=user.id, snack_id=snack.id)
    db_session.add(vote2)
    with pytest.raises(IntegrityError):
        db_session.flush()
