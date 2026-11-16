"""Database engine and session management with SQLAlchemy 2.0."""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()

# Engine configured with pool_size >= 15 and pool_pre_ping=True
engine = create_engine(
    settings.sqlalchemy_database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=1800,  # Recycle connections older than 30 minutes
    echo=False,
)

# Standard sessionmaker for sync database transactions
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a managed database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
