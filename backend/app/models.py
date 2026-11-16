"""SQLAlchemy 2.0 ORM models for Snack Overflow."""

import enum
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    """User authorization roles."""
    ADMIN = "admin"
    MEMBER = "member"


class SnackCategory(str, enum.Enum):
    """Pantry snack categories."""
    SWEET = "sweet"
    SAVOURY = "savoury"
    DRINK = "drink"
    HEALTHY_ISH = "healthy-ish"


class ActivityAction(str, enum.Enum):
    """Actions performed on pantry items."""
    RESTOCKED = "restocked"
    CONSUMED = "consumed"


class User(Base):
    """Registered team member or admin."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(
            UserRole,
            name="user_role",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
        default=UserRole.MEMBER,
        server_default=UserRole.MEMBER.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="user",
    )


class Snack(Base):
    """Pantry snack inventory item."""

    __tablename__ = "snacks"
    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_snacks_quantity_non_negative"),
        CheckConstraint("low_stock_threshold >= 0", name="ck_snacks_threshold_non_negative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    category: Mapped[SnackCategory] = mapped_column(
        SQLEnum(
            SnackCategory,
            name="snack_category",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
        default=0,
        server_default="0",
    )
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=5,
        server_default="5",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    votes: Mapped[List["Vote"]] = relationship(
        "Vote",
        back_populates="snack",
        cascade="all, delete-orphan",
    )
    activities: Mapped[List["Activity"]] = relationship(
        "Activity",
        back_populates="snack",
    )

    @property
    def status(self) -> str:
        """
        Status is strictly DERIVED from quantity and low_stock_threshold (never stored):
        - 'stocked': quantity > low_stock_threshold
        - 'running_low': 1 <= quantity <= low_stock_threshold
        - 'gone': quantity == 0
        """
        if self.quantity > self.low_stock_threshold:
            return "stocked"
        elif self.quantity > 0:
            return "running_low"
        return "gone"


class Vote(Base):
    """
    Snack voting table.
    Enforces exactly one vote per user per snack using a composite primary key.
    """

    __tablename__ = "votes"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    snack_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("snacks.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,  # Fast lookup for snack vote totals
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="votes")
    snack: Mapped["Snack"] = relationship("Snack", back_populates="votes")


class Activity(Base):
    """
    Audit log of all stock transactions (restock/consume).
    Must be recorded within the same transaction as the stock update.
    """

    __tablename__ = "activities"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_activities_amount_positive"),
        Index("ix_activities_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    snack_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("snacks.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Snapshot of snack name so pantry audit logs survive snack deletion
    snack_name: Mapped[str] = mapped_column(String(150), nullable=False)
    action: Mapped[ActivityAction] = mapped_column(
        SQLEnum(
            ActivityAction,
            name="activity_action",
            values_callable=lambda obj: [e.value for e in obj],
            native_enum=True,
        ),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_after: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="activities")
    snack: Mapped[Optional["Snack"]] = relationship("Snack", back_populates="activities")
