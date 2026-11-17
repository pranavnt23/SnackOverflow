"""Test Suite: Stock Operations and Transactional Audit Integrity.

Covers:
3. Quantity Never Negative: Stock cannot drop below zero; excessive consume returns 409
   and leaves database inventory completely intact.
4. Activity Recorded: Every successful consume and restock writes an activity audit row
   in the SAME transaction, while failed attempts record zero activity rows.
"""

from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Activity, ActivityAction, Snack, SnackCategory, User


def test_quantity_never_negative(
    client: TestClient,
    db_session: Session,
    member_headers: Dict[str, str],
):
    """
    Test 3: Quantity Never Negative.
    
    Verifies that:
    1. Consuming more than available stock yields 409 INSUFFICIENT_STOCK.
    2. The database quantity is strictly preserved without modification.
    3. When stock is reduced to 0, subsequent consume attempts still fail cleanly
       with the contextual message 'Someone beat you to the last packet!'.
    4. The inventory level never drops below 0.
    """
    # 1. Arrange: Create a snack with 5 packets
    snack = Snack(
        name="Smoky BBQ Almonds",
        category=SnackCategory.SAVOURY,
        quantity=5,
        low_stock_threshold=2,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    snack_id = snack.id

    # 2. Act & Assert: Attempt to consume 10 (exceeds stock of 5)
    res_over = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 10},
        headers=member_headers,
    )
    assert res_over.status_code == 409
    body_over = res_over.json()
    assert body_over["error"]["code"] == "INSUFFICIENT_STOCK"
    assert "Only 5 packets left in the pantry" in body_over["error"]["message"]

    # Verify database quantity was NOT changed
    db_session.expire_all()
    snack_refreshed = db_session.get(Snack, snack_id)
    assert snack_refreshed.quantity == 5

    # 3. Act & Assert: Attempt to consume 6 (still exceeds stock of 5 by 1)
    res_over_single = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 6},
        headers=member_headers,
    )
    assert res_over_single.status_code == 409
    assert res_over_single.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verify quantity still untouched
    db_session.expire_all()
    assert db_session.get(Snack, snack_id).quantity == 5

    # 4. Act & Assert: Consume exactly all 5 packets
    res_consume_all = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 5},
        headers=member_headers,
    )
    assert res_consume_all.status_code == 200
    assert res_consume_all.json()["quantity"] == 0
    assert res_consume_all.json()["status"] == "gone"

    # Verify quantity is now exactly 0
    db_session.expire_all()
    assert db_session.get(Snack, snack_id).quantity == 0

    # 5. Act & Assert: Attempt to consume 1 packet when stock is 0
    res_zero = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 1},
        headers=member_headers,
    )
    assert res_zero.status_code == 409
    body_zero = res_zero.json()
    assert body_zero["error"]["code"] == "INSUFFICIENT_STOCK"
    assert body_zero["error"]["message"] == "Someone beat you to the last packet!"

    # Invariant holds: quantity is still 0, never negative
    db_session.expire_all()
    assert db_session.get(Snack, snack_id).quantity == 0


def test_activity_recorded_for_consume_and_restock(
    client: TestClient,
    db_session: Session,
    admin_headers: Dict[str, str],
    admin_user: User,
    member_headers: Dict[str, str],
    member_user: User,
):
    """
    Test 4: Activity Audit Recording.
    
    Verifies that:
    1. Admin restock logs an activity row with action='restocked', amount, quantity_after.
    2. Member consume logs an activity row with action='consumed', amount, quantity_after.
    3. Failed consume (due to insufficient stock) creates NO activity rows.
    4. Confirms database transaction boundary ensures no activity row is written on failure.
    """
    # 1. Arrange: Create initial snack with 10 units
    snack = Snack(
        name="Organic Dried Mango",
        category=SnackCategory.SWEET,
        quantity=10,
        low_stock_threshold=3,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    snack_id = snack.id

    # Initial activities count must be 0
    initial_activities = db_session.query(Activity).filter(Activity.snack_id == snack_id).count()
    assert initial_activities == 0

    # 2. Restock: Admin restocks 15 units (10 -> 25)
    res_restock = client.post(
        f"/snacks/{snack_id}/restock",
        json={"amount": 15},
        headers=admin_headers,
    )
    assert res_restock.status_code == 200
    assert res_restock.json()["quantity"] == 25

    # Verify restock activity row
    db_session.expire_all()
    restock_activities = (
        db_session.query(Activity)
        .filter(Activity.snack_id == snack_id, Activity.action == ActivityAction.RESTOCKED)
        .all()
    )
    assert len(restock_activities) == 1
    act_restock = restock_activities[0]
    assert act_restock.action == ActivityAction.RESTOCKED
    assert act_restock.amount == 15
    assert act_restock.quantity_after == 25
    assert act_restock.snack_name == "Organic Dried Mango"
    assert act_restock.user_id == admin_user.id

    # 3. Consume: Member consumes 7 units (25 -> 18)
    res_consume = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 7},
        headers=member_headers,
    )
    assert res_consume.status_code == 200
    assert res_consume.json()["quantity"] == 18

    # Verify consume activity row
    db_session.expire_all()
    consume_activities = (
        db_session.query(Activity)
        .filter(Activity.snack_id == snack_id, Activity.action == ActivityAction.CONSUMED)
        .all()
    )
    assert len(consume_activities) == 1
    act_consume = consume_activities[0]
    assert act_consume.action == ActivityAction.CONSUMED
    assert act_consume.amount == 7
    assert act_consume.quantity_after == 18
    assert act_consume.snack_name == "Organic Dried Mango"
    assert act_consume.user_id == member_user.id

    # Total activities at this point should be 2
    total_activities = db_session.query(Activity).filter(Activity.snack_id == snack_id).count()
    assert total_activities == 2

    # 4. Failed Consume: Member attempts to consume 50 units (only 18 available)
    res_failed = client.post(
        f"/snacks/{snack_id}/consume",
        json={"amount": 50},
        headers=member_headers,
    )
    assert res_failed.status_code == 409
    assert res_failed.json()["error"]["code"] == "INSUFFICIENT_STOCK"

    # Verify NO new activity row was written for the failed transaction
    db_session.expire_all()
    activities_after_failure = db_session.query(Activity).filter(Activity.snack_id == snack_id).count()
    assert activities_after_failure == 2, (
        f"Expected activity count to remain 2 after failed consume, found {activities_after_failure}"
    )
