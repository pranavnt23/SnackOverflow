"""Pytest configuration, test database isolation, and fixtures for Snack Overflow."""

import os
from typing import Generator, List, Dict, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.database import Base, get_db
from app.main import app
from app.models import Snack, User, UserRole
from app.security import create_access_token, hash_password

settings = get_settings()

# ==============================================================================
# SAFETY INVARIANT ENFORCEMENT
# Refuse to run test suite if TEST_DATABASE_URL is missing or equals DATABASE_URL.
# This prevents accidental truncation or data corruption on primary/production DB.
# ==============================================================================
raw_test_url = settings.TEST_DATABASE_URL
raw_prod_url = settings.DATABASE_URL

if not raw_test_url:
    pytest.exit(
        "CRITICAL ERROR: TEST_DATABASE_URL is not configured in environment (.env). "
        "Refusing to execute tests against primary/production database.",
        returncode=1,
    )

if raw_test_url.strip() == raw_prod_url.strip():
    pytest.exit(
        f"SAFETY VIOLATION: TEST_DATABASE_URL ({raw_test_url}) is identical to DATABASE_URL! "
        "Tests must run on a completely dedicated, isolated test database to protect application data.",
        returncode=1,
    )

# Dedicated SQLAlchemy engine for test database
test_engine = create_engine(
    settings.sqlalchemy_test_database_url,
    pool_size=25,
    max_overflow=15,
    pool_pre_ping=True,
    echo=False,
)

TestingSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database_schema():
    """
    Session-scoped fixture: Creates the database schema once on the test database.
    Runs once before any test executes.
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    # Tables remain intact for subsequent runs or can be inspected if needed.


@pytest.fixture(autouse=True)
def truncate_tables_between_tests():
    """
    Function-scoped fixture: Truncates all tables and resets primary key sequences
    between tests. Ensures 100% test isolation with zero residual state.
    """
    with test_engine.begin() as conn:
        conn.execute(
            text("TRUNCATE TABLE users, snacks, votes, activities RESTART IDENTITY CASCADE;")
        )
    yield


@pytest.fixture(autouse=True)
def override_database_dependency():
    """
    Function-scoped fixture: Overrides FastAPI's get_db dependency so every
    HTTP request in tests uses a session connected to TEST_DATABASE_URL.
    """
    def _get_test_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Provides a direct database session for tests to inspect or arrange database state.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient configured with test database overrides.
    """
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# AUTHENTICATION & USER FIXTURES
# ==============================================================================

@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Creates and persists an admin user in the test database."""
    admin = User(
        name="Admin Test User",
        email="admin@snack.local",
        password_hash=hash_password("Admin@123"),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Returns a valid JWT access token for the admin user."""
    return create_access_token(str(admin_user.id))


@pytest.fixture
def admin_headers(admin_token: str) -> Dict[str, str]:
    """Returns HTTP headers dictionary with admin Bearer token."""
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def member_user(db_session: Session) -> User:
    """Creates and persists a standard team member in the test database."""
    member = User(
        name="Member Test User",
        email="member@snack.local",
        password_hash=hash_password("Member@123"),
        role=UserRole.MEMBER,
    )
    db_session.add(member)
    db_session.commit()
    db_session.refresh(member)
    return member


@pytest.fixture
def member_token(member_user: User) -> str:
    """Returns a valid JWT access token for the member user."""
    return create_access_token(str(member_user.id))


@pytest.fixture
def member_headers(member_token: str) -> Dict[str, str]:
    """Returns HTTP headers dictionary with member Bearer token."""
    return {"Authorization": f"Bearer {member_token}"}


@pytest.fixture
def auth_tokens(admin_headers: Dict[str, str], member_headers: Dict[str, str]) -> Dict[str, str]:
    """Convenience fixture matching existing tests' auth_tokens interface."""
    return {
        "admin": admin_headers["Authorization"],
        "member": member_headers["Authorization"],
    }


@pytest.fixture
def extra_members(db_session: Session) -> List[Dict[str, Any]]:
    """
    Creates 10 distinct registered member users in the test database,
    each with their own ID, email, and valid JWT Bearer header.
    Essential for concurrency tests where multiple independent users act simultaneously.
    """
    members = []
    for i in range(1, 11):
        user = User(
            name=f"Concurrency Member {i}",
            email=f"concurrency_member_{i}@snack.local",
            password_hash=hash_password("MemberPassword@123"),
            role=UserRole.MEMBER,
        )
        db_session.add(user)
        members.append(user)

    db_session.commit()

    result = []
    for user in members:
        db_session.refresh(user)
        token = create_access_token(str(user.id))
        result.append({
            "user": user,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        })

    return result
