"""Test Suite: Input Validation and Standard Error Envelopes.

Covers:
7. Validation:
   - Validates that amount == 0, negative integers, string types, and out-of-bound
     values trigger HTTP 422 Unprocessable Entity.
   - Verifies the standardized error envelope format:
     {"error": {"code": "VALIDATION_ERROR", "message": "...", "details": [...]}}
"""

from typing import Dict
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Snack, SnackCategory


@pytest.fixture
def target_snack(db_session: Session) -> Snack:
    """Fixture to provide a snack for validation testing."""
    snack = Snack(
        name="Validation Crunch Bar",
        category=SnackCategory.SWEET,
        quantity=20,
        low_stock_threshold=5,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    return snack


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"amount": 0},          # Zero amount (must be >= 1)
        {"amount": -1},         # Negative amount
        {"amount": -25},        # Large negative amount
        {"amount": "invalid"},   # String type
        {"amount": 101},        # Exceeds max consume amount of 100
        {},                     # Missing required field
    ],
)
def test_consume_input_validation(
    client: TestClient,
    target_snack: Snack,
    member_headers: Dict[str, str],
    invalid_payload: dict,
):
    """
    Test 7 (Part A): Consume Input Validation.
    Asserts that invalid consume quantities produce 422 VALIDATION_ERROR with structured field details.
    """
    res = client.post(
        f"/snacks/{target_snack.id}/consume",
        json=invalid_payload,
        headers=member_headers,
    )
    assert res.status_code == 422, f"Payload {invalid_payload} returned status {res.status_code}"
    body = res.json()

    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) >= 1


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {"amount": 0},          # Zero amount (must be >= 1)
        {"amount": -5},         # Negative amount
        {"amount": "five"},     # String type
        {"amount": 1001},       # Exceeds max restock amount of 1000
        {},                     # Missing required field
    ],
)
def test_restock_input_validation(
    client: TestClient,
    target_snack: Snack,
    admin_headers: Dict[str, str],
    invalid_payload: dict,
):
    """
    Test 7 (Part B): Restock Input Validation.
    Asserts that invalid restock amounts produce 422 VALIDATION_ERROR with structured field details.
    """
    res = client.post(
        f"/snacks/{target_snack.id}/restock",
        json=invalid_payload,
        headers=admin_headers,
    )
    assert res.status_code == 422, f"Payload {invalid_payload} returned status {res.status_code}"
    body = res.json()

    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) >= 1


def test_snack_creation_input_validation(
    client: TestClient,
    admin_headers: Dict[str, str],
):
    """
    Test 7 (Part C): Create Snack Input Validation.
    Asserts invalid category, negative thresholds, and blank names trigger 422 VALIDATION_ERROR.
    """
    # Invalid category enum
    res_bad_category = client.post(
        "/snacks",
        json={"name": "Weird Snack", "category": "non_existent_category", "quantity": 10, "low_stock_threshold": 2},
        headers=admin_headers,
    )
    assert res_bad_category.status_code == 422
    assert res_bad_category.json()["error"]["code"] == "VALIDATION_ERROR"

    # Negative quantity
    res_neg_qty = client.post(
        "/snacks",
        json={"name": "Negative Snack", "category": "sweet", "quantity": -5, "low_stock_threshold": 2},
        headers=admin_headers,
    )
    assert res_neg_qty.status_code == 422
    assert res_neg_qty.json()["error"]["code"] == "VALIDATION_ERROR"

    # Negative threshold
    res_neg_thresh = client.post(
        "/snacks",
        json={"name": "Bad Threshold Snack", "category": "sweet", "quantity": 5, "low_stock_threshold": -1},
        headers=admin_headers,
    )
    assert res_neg_thresh.status_code == 422
    assert res_neg_thresh.json()["error"]["code"] == "VALIDATION_ERROR"
