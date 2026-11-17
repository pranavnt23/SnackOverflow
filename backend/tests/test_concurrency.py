"""Test Suite: Concurrency, Thread Synchronization, and Race-Condition Elimination.

This test file is designed to demonstrate and verify the system's core database-level
atomicity invariants under high concurrent load:
1. Concurrent Consume: 10 distinct users competing simultaneously for 3 items.
2. Concurrent Duplicate Votes: 1 user dispatching 10 simultaneous vote requests.

Both tests employ `ThreadPoolExecutor` paired with `threading.Barrier(10)` to synchronize
thread release to the exact same millisecond, maximizing contention at the database engine.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Activity, ActivityAction, Snack, SnackCategory, User, Vote


def test_concurrent_consume_with_barrier(
    client: TestClient,
    db_session: Session,
    extra_members: List[Dict[str, Any]],
):
    """
    Test 1: Concurrency (Most Important Requirement).
    
    Setup:
      - 1 snack with initial quantity = 3, threshold = 1.
      - 10 distinct registered members (from extra_members fixture).
    
    Execution:
      - Each member calls POST /snacks/{id}/consume with {"amount": 1} at the exact same moment.
      - A threading.Barrier(10) holds all 10 worker threads until every thread is ready,
        then releases them simultaneously.
      - Each request executes over its own database connection in FastAPI's dependency session lifecycle.
    
    Invariants Asserted:
      - Exactly 3 requests succeed with HTTP 200 OK.
      - Exactly 7 requests fail with HTTP 409 Conflict.
      - All 7 failure envelopes contain code == "INSUFFICIENT_STOCK".
      - Final database snack quantity == 0 (no negative quantity drift).
      - Exactly 3 activity rows are inserted in the `activities` table (atomic audit invariant).
    """
    # 1. Arrange: Create the target snack with exactly 3 items in stock
    snack = Snack(
        name="Limited Edition Pistachio Halva",
        category=SnackCategory.SWEET,
        quantity=3,
        low_stock_threshold=1,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    snack_id = snack.id

    assert len(extra_members) == 10, "Requires exactly 10 distinct member users"

    # 2. Thread Synchronization Barrier:
    # A barrier for 10 parties ensures that all 10 worker threads are initialized,
    # spawned, and waiting before any single HTTP request is dispatched.
    barrier = threading.Barrier(10)

    def worker_consume(member_data: Dict[str, Any]):
        auth_headers = member_data["headers"]
        # Synchronize all threads at the gate
        barrier.wait()
        # Fire request concurrently
        response = client.post(
            f"/snacks/{snack_id}/consume",
            json={"amount": 1},
            headers=auth_headers,
        )
        return response

    # 3. Act: Execute 10 simultaneous consumption requests across 10 threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_consume, member) for member in extra_members]
        responses = [f.result() for f in futures]

    # 4. Assert: Inspect HTTP response codes and error envelopes
    status_codes = [r.status_code for r in responses]
    success_responses = [r for r in responses if r.status_code == 200]
    conflict_responses = [r for r in responses if r.status_code == 409]

    # Exactly 3 succeed, exactly 7 fail
    assert len(success_responses) == 3, f"Expected 3 successes, got {len(success_responses)} (all codes: {status_codes})"
    assert len(conflict_responses) == 7, f"Expected 7 conflicts, got {len(conflict_responses)} (all codes: {status_codes})"

    # Verify that all 7 conflicts have the correct standardized error code
    for r in conflict_responses:
        body = r.json()
        assert "error" in body, f"Response missing error envelope: {body}"
        assert body["error"]["code"] == "INSUFFICIENT_STOCK", f"Unexpected code: {body['error']['code']}"
        # Message should either be 'Someone beat you to the last packet!' or indicate remaining packets
        assert "Someone beat you" in body["error"]["message"]

    # 5. Assert: Inspect Database State directly
    # Expire session identity map to force fresh SELECT from PostgreSQL
    db_session.expire_all()
    refreshed_snack = db_session.get(Snack, snack_id)
    assert refreshed_snack is not None
    assert refreshed_snack.quantity == 0, f"Expected final quantity 0, found {refreshed_snack.quantity}"

    # Verify activity audit trail: exactly 3 rows recorded
    activities = (
        db_session.query(Activity)
        .filter(Activity.snack_id == snack_id, Activity.action == ActivityAction.CONSUMED)
        .all()
    )
    assert len(activities) == 3, f"Expected 3 activity rows, found {len(activities)}"
    for act in activities:
        assert act.amount == 1
        assert act.snack_name == "Limited Edition Pistachio Halva"
        assert act.user_id in [m["user"].id for m in extra_members]


def test_concurrent_duplicate_votes_with_barrier(
    client: TestClient,
    db_session: Session,
    member_headers: Dict[str, str],
    member_user: User,
):
    """
    Test 2: Concurrent Duplicate Votes.
    
    Setup:
      - 1 snack in pantry.
      - 1 user attempts to vote for the same snack 10 times simultaneously.
    
    Execution:
      - ThreadPoolExecutor with threading.Barrier(10) dispatches 10 POST /snacks/{id}/vote
        requests from the same user account at the exact same millisecond.
    
    Invariants Asserted:
      - Exactly 1 request succeeds with HTTP 201 Created.
      - Exactly 9 requests fail with HTTP 409 Conflict (code == "ALREADY_VOTED").
      - Exactly 1 row exists in the `votes` table for (user_id, snack_id).
      - Proves that PostgreSQL composite primary key (user_id, snack_id) and transaction
        isolation eliminate race conditions under concurrent client duplication.
    """
    # 1. Arrange: Create a snack to vote on
    snack = Snack(
        name="Artisanal Cold Brew",
        category=SnackCategory.DRINK,
        quantity=20,
        low_stock_threshold=5,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    snack_id = snack.id

    # 2. Thread Synchronization Barrier for 10 concurrent requests
    barrier = threading.Barrier(10)

    def worker_vote(thread_idx: int):
        barrier.wait()
        response = client.post(
            f"/snacks/{snack_id}/vote",
            headers=member_headers,
        )
        return response

    # 3. Act: Fire 10 simultaneous voting requests from the SAME user
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_vote, i) for i in range(10)]
        responses = [f.result() for f in futures]

    # 4. Assert: Inspect response codes
    status_codes = [r.status_code for r in responses]
    created_responses = [r for r in responses if r.status_code == 201]
    conflict_responses = [r for r in responses if r.status_code == 409]

    assert len(created_responses) == 1, f"Expected exactly 1 vote success (201), got {len(created_responses)}: {status_codes}"
    assert len(conflict_responses) == 9, f"Expected 9 conflict failures (409), got {len(conflict_responses)}: {status_codes}"

    # Verify winning response
    winner_body = created_responses[0].json()
    assert winner_body["snack_id"] == snack_id
    assert winner_body["has_voted"] is True
    assert winner_body["vote_count"] == 1

    # Verify all 9 conflict responses carry standardized error
    for r in conflict_responses:
        body = r.json()
        assert body["error"]["code"] == "ALREADY_VOTED"
        assert body["error"]["message"] == "You have already voted for this snack"

    # 5. Assert: Inspect Database state
    db_session.expire_all()
    vote_rows = (
        db_session.query(Vote)
        .filter(Vote.snack_id == snack_id, Vote.user_id == member_user.id)
        .all()
    )
    assert len(vote_rows) == 1, f"Expected exactly 1 row in votes table, found {len(vote_rows)}"
