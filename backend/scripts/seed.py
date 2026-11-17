"""Idempotent database seed script for development and testing."""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import func
from app.database import SessionLocal
from app.models import Snack, SnackCategory, User, UserRole
from app.security import hash_password

# Demo Users
DEMO_USERS = [
    {
        "name": "Demo Admin",
        "email": "admin@snack.local",
        "raw_password": "Admin@123",
        "role": UserRole.ADMIN,
    },
    {
        "name": "Demo Member",
        "email": "member@snack.local",
        "raw_password": "Member@123",
        "role": UserRole.MEMBER,
    },
]

# Sample Pantry Snacks
# Covers all 4 categories, all 3 statuses (stocked, running_low, gone), with several custom thresholds
DEMO_SNACKS = [
    # Sweet
    {
        "name": "Dark Chocolate Almonds",
        "category": SnackCategory.SWEET,
        "quantity": 25,
        "low_stock_threshold": 5,  # Status: stocked (25 > 5)
    },
    {
        "name": "Gummy Bears",
        "category": SnackCategory.SWEET,
        "quantity": 3,
        "low_stock_threshold": 5,  # Status: running_low (1 <= 3 <= 5)
    },
    {
        "name": "Chocolate Chip Cookies",
        "category": SnackCategory.SWEET,
        "quantity": 0,
        "low_stock_threshold": 5,  # Status: gone (0)
    },
    # Savoury
    {
        "name": "Sea Salt Kettle Chips",
        "category": SnackCategory.SAVOURY,
        "quantity": 18,
        "low_stock_threshold": 5,  # Status: stocked (18 > 5)
    },
    {
        "name": "Roasted Cashews",
        "category": SnackCategory.SAVOURY,
        "quantity": 4,
        "low_stock_threshold": 5,  # Status: running_low (1 <= 4 <= 5)
    },
    {
        "name": "White Cheddar Popcorn",
        "category": SnackCategory.SAVOURY,
        "quantity": 0,
        "low_stock_threshold": 5,  # Status: gone (0)
    },
    {
        "name": "Spicy Trail Mix",
        "category": SnackCategory.SAVOURY,
        "quantity": 7,
        "low_stock_threshold": 10,  # Status: running_low (custom threshold: 1 <= 7 <= 10)
    },
    # Drink
    {
        "name": "Sparkling Lime Water",
        "category": SnackCategory.DRINK,
        "quantity": 32,
        "low_stock_threshold": 10,  # Status: stocked (custom threshold: 32 > 10)
    },
    {
        "name": "Cold Brew Coffee Can",
        "category": SnackCategory.DRINK,
        "quantity": 2,
        "low_stock_threshold": 5,  # Status: running_low (1 <= 2 <= 5)
    },
    {
        "name": "Ginger Kombucha",
        "category": SnackCategory.DRINK,
        "quantity": 0,
        "low_stock_threshold": 4,  # Status: gone (custom threshold: 0)
    },
    # Healthy-ish
    {
        "name": "Dried Mango Slices",
        "category": SnackCategory.HEALTHY_ISH,
        "quantity": 14,
        "low_stock_threshold": 5,  # Status: stocked (14 > 5)
    },
    {
        "name": "Peanut Butter Protein Bar",
        "category": SnackCategory.HEALTHY_ISH,
        "quantity": 3,
        "low_stock_threshold": 6,  # Status: running_low (custom threshold: 1 <= 3 <= 6)
    },
    {
        "name": "Baked Pita Chips",
        "category": SnackCategory.HEALTHY_ISH,
        "quantity": 0,
        "low_stock_threshold": 5,  # Status: gone (0)
    },
]


def seed_database() -> None:
    """Populate database idempotently with demo users and sample snacks."""
    db = SessionLocal()
    try:
        print("🌱 Seeding Snack Overflow database...")

        # 1. Seed Users
        for user_data in DEMO_USERS:
            email = user_data["email"]
            existing_user = (
                db.query(User)
                .filter(func.lower(User.email) == email.lower())
                .first()
            )

            hashed_pw = hash_password(user_data["raw_password"])

            if existing_user:
                existing_user.name = user_data["name"]
                existing_user.password_hash = hashed_pw
                existing_user.role = user_data["role"]
                print(f"  [User Updated] {email} ({user_data['role'].value})")
            else:
                new_user = User(
                    name=user_data["name"],
                    email=email,
                    password_hash=hashed_pw,
                    role=user_data["role"],
                )
                db.add(new_user)
                print(f"  [User Created] {email} ({user_data['role'].value})")

        db.commit()

        # 2. Seed Snacks
        for snack_data in DEMO_SNACKS:
            name = snack_data["name"]
            existing_snack = (
                db.query(Snack)
                .filter(func.lower(Snack.name) == name.lower())
                .first()
            )

            if existing_snack:
                existing_snack.category = snack_data["category"]
                existing_snack.quantity = snack_data["quantity"]
                existing_snack.low_stock_threshold = snack_data["low_stock_threshold"]
                status_label = existing_snack.status
                print(
                    f"  [Snack Updated] {name} | Qty: {snack_data['quantity']} | "
                    f"Thresh: {snack_data['low_stock_threshold']} | Status: {status_label}"
                )
            else:
                new_snack = Snack(
                    name=name,
                    category=snack_data["category"],
                    quantity=snack_data["quantity"],
                    low_stock_threshold=snack_data["low_stock_threshold"],
                )
                db.add(new_snack)
                status_label = new_snack.status
                print(
                    f"  [Snack Created] {name} | Qty: {snack_data['quantity']} | "
                    f"Thresh: {snack_data['low_stock_threshold']} | Status: {status_label}"
                )

        db.commit()
        print("✅ Database seeding complete!")

    except Exception as exc:
        db.rollback()
        print(f"❌ Error during database seeding: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
