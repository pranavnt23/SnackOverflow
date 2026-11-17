"""Test suite for snack inventory endpoints, filtering, and summary."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func

from app.database import SessionLocal
from app.main import app
from app.models import Activity, ActivityAction, Snack, SnackCategory, User, UserRole, Vote

client = TestClient(app)


@pytest.fixture(scope="module")
def auth_tokens():
    """Obtain JWT tokens for admin and member demo users."""
    admin_res = client.post(
        "/auth/login",
        json={"email": "admin@snack.local", "password": "Admin@123"},
    )
    assert admin_res.status_code == 200, f"Admin login failed: {admin_res.text}"
    admin_token = admin_res.json()["access_token"]

    member_res = client.post(
        "/auth/login",
        json={"email": "member@snack.local", "password": "Member@123"},
    )
    assert member_res.status_code == 200, f"Member login failed: {member_res.text}"
    member_token = member_res.json()["access_token"]

    return {
        "admin": f"Bearer {admin_token}",
        "member": f"Bearer {member_token}",
    }


def test_get_snacks_requires_auth():
    """Verify /snacks requires authentication."""
    res = client.get("/snacks")
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "UNAUTHORIZED"


def test_get_snacks_pagination(auth_tokens):
    """Verify pagination returns items, total, page, page_size, total_pages."""
    res = client.get("/snacks?page=1&page_size=5", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 200
    data = res.json()

    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["page_size"] == 5
    assert len(data["items"]) <= 5
    assert data["total_pages"] >= 1

    # Verify snack item schema fields
    item = data["items"][0]
    assert "status" in item
    assert "vote_count" in item
    assert "has_voted" in item
    assert item["status"] in ["stocked", "running_low", "gone"]


def test_get_snacks_category_filter(auth_tokens):
    """Verify filtering snacks by category in SQL."""
    res = client.get("/snacks?category=sweet", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    for item in data["items"]:
        assert item["category"] == "sweet"


def test_get_snacks_status_filter(auth_tokens):
    """Verify filtering snacks by SQL CASE-derived status."""
    # Test 'gone' (quantity == 0)
    res_gone = client.get("/snacks?status=gone", headers={"Authorization": auth_tokens["member"]})
    assert res_gone.status_code == 200
    gone_data = res_gone.json()
    for item in gone_data["items"]:
        assert item["status"] == "gone"
        assert item["quantity"] == 0

    # Test 'running_low' (1 <= quantity <= low_stock_threshold)
    res_low = client.get("/snacks?status=running_low", headers={"Authorization": auth_tokens["member"]})
    assert res_low.status_code == 200
    low_data = res_low.json()
    for item in low_data["items"]:
        assert item["status"] == "running_low"
        assert 1 <= item["quantity"] <= item["low_stock_threshold"]

    # Test 'stocked' (quantity > low_stock_threshold)
    res_stocked = client.get("/snacks?status=stocked", headers={"Authorization": auth_tokens["member"]})
    assert res_stocked.status_code == 200
    stocked_data = res_stocked.json()
    for item in stocked_data["items"]:
        assert item["status"] == "stocked"
        assert item["quantity"] > item["low_stock_threshold"]


def test_get_snacks_invalid_enum_validation_error(auth_tokens):
    """Verify invalid category or status enum produces 422 VALIDATION_ERROR with details."""
    res = client.get("/snacks?status=invalid_status", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert any(d["field"] == "status" for d in body["error"]["details"])


def test_get_snacks_search_and_escaping(auth_tokens):
    """Verify case-insensitive search and SQL LIKE wildcard escaping."""
    # Case-insensitive partial search
    res = client.get("/snacks?search=almond", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any("almond" in item["name"].lower() for item in data["items"])

    # Escaping % wildcard: searching for '%' should not match all snacks
    res_percent = client.get("/snacks?search=%", headers={"Authorization": auth_tokens["member"]})
    assert res_percent.status_code == 200
    percent_data = res_percent.json()
    # Unless a snack literally has '%' in its name, total is 0
    assert percent_data["total"] == 0


def test_get_snacks_summary_route_precedence(auth_tokens):
    """
    Verify /snacks/summary is matched as the summary endpoint,
    NOT parsed as /snacks/{id} with id='summary'.
    """
    res = client.get("/snacks/summary", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 200
    data = res.json()

    assert "stocked" in data
    assert "running_low" in data
    assert "gone" in data
    assert "total" in data
    assert "snack_of_the_week" in data
    assert data["total"] == data["stocked"] + data["running_low"] + data["gone"]


def test_get_snack_by_id_success_and_404(auth_tokens):
    """Verify /snacks/{id} returns snack details and 404 NOT_FOUND when missing."""
    # 1. Fetch valid snack from list
    list_res = client.get("/snacks?page_size=1", headers={"Authorization": auth_tokens["member"]})
    snack_id = list_res.json()["items"][0]["id"]

    res = client.get(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["member"]})
    assert res.status_code == 200
    assert res.json()["id"] == snack_id

    # 2. Non-existent snack
    res_missing = client.get("/snacks/999999", headers={"Authorization": auth_tokens["member"]})
    assert res_missing.status_code == 404
    assert res_missing.json()["error"]["code"] == "NOT_FOUND"


def test_post_snack_permissions_and_duplicate_conflict(auth_tokens):
    """Verify POST /snacks requires admin and returns 409 DUPLICATE_NAME on conflict."""
    payload = {
        "name": " Unique Artisan Pretzel ",
        "category": "savoury",
        "quantity": 12,
        "low_stock_threshold": 4,
    }

    # 1. Member forbidden
    res_member = client.post("/snacks", json=payload, headers={"Authorization": auth_tokens["member"]})
    assert res_member.status_code == 403
    assert res_member.json()["error"]["code"] == "FORBIDDEN"

    # 2. Admin creates successfully
    res_admin = client.post("/snacks", json=payload, headers={"Authorization": auth_tokens["admin"]})
    assert res_admin.status_code == 201
    created_data = res_admin.json()
    assert created_data["name"] == "Unique Artisan Pretzel"  # Trimmed
    assert created_data["quantity"] == 12
    snack_id = created_data["id"]

    # 3. Duplicate name returns 409 DUPLICATE_NAME (via IntegrityError catch)
    res_dup = client.post("/snacks", json=payload, headers={"Authorization": auth_tokens["admin"]})
    assert res_dup.status_code == 409
    assert res_dup.json()["error"]["code"] == "DUPLICATE_NAME"

    # Clean up test snack
    client.delete(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["admin"]})


def test_patch_snack_forbids_quantity(auth_tokens):
    """Verify PATCH /snacks/{id} forbids editing quantity (extra='forbid')."""
    # 1. Create a temporary snack
    create_res = client.post(
        "/snacks",
        json={"name": "Patch Test Snack", "category": "sweet", "quantity": 10, "low_stock_threshold": 3},
        headers={"Authorization": auth_tokens["admin"]},
    )
    snack_id = create_res.json()["id"]

    try:
        # 2. Attempt to update quantity -> must fail with 422 VALIDATION_ERROR
        res_qty = client.patch(
            f"/snacks/{snack_id}",
            json={"quantity": 20},
            headers={"Authorization": auth_tokens["admin"]},
        )
        assert res_qty.status_code == 422
        body = res_qty.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert any(d["field"] == "quantity" for d in body["error"]["details"])

        # 3. Valid metadata update succeeds
        res_valid = client.patch(
            f"/snacks/{snack_id}",
            json={"name": "Renamed Patch Test Snack", "low_stock_threshold": 6},
            headers={"Authorization": auth_tokens["admin"]},
        )
        assert res_valid.status_code == 200
        assert res_valid.json()["name"] == "Renamed Patch Test Snack"
        assert res_valid.json()["low_stock_threshold"] == 6
        assert res_valid.json()["quantity"] == 10  # Untouched

    finally:
        client.delete(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["admin"]})


def test_delete_snack_cascades_votes_and_preserves_activities(auth_tokens):
    """Verify DELETE /snacks/{id} cascades votes and sets activity.snack_id to NULL."""
    # Create snack
    create_res = client.post(
        "/snacks",
        json={"name": "Deletion Test Snack", "category": "drink", "quantity": 5, "low_stock_threshold": 2},
        headers={"Authorization": auth_tokens["admin"]},
    )
    snack_id = create_res.json()["id"]

    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.email == "admin@snack.local").first()

        # Add a vote
        vote = Vote(user_id=admin_user.id, snack_id=snack_id)
        db.add(vote)

        # Add an activity log
        activity = Activity(
            user_id=admin_user.id,
            snack_id=snack_id,
            snack_name="Deletion Test Snack",
            action=ActivityAction.RESTOCKED,
            amount=5,
            quantity_after=5,
        )
        db.add(activity)
        db.commit()
        activity_id = activity.id

        # Member cannot delete
        res_member_del = client.delete(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["member"]})
        assert res_member_del.status_code == 403

        # Admin deletes
        res_del = client.delete(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["admin"]})
        assert res_del.status_code == 204

        # Snack is gone
        res_get = client.get(f"/snacks/{snack_id}", headers={"Authorization": auth_tokens["admin"]})
        assert res_get.status_code == 404

        # Vote was cascaded
        remaining_vote = db.query(Vote).filter(Vote.snack_id == snack_id).first()
        assert remaining_vote is None

        # Activity was kept with snack_id=None and snack_name preserved
        db.expire_all()
        remaining_activity = db.get(Activity, activity_id)
        assert remaining_activity is not None
        assert remaining_activity.snack_id is None
        assert remaining_activity.snack_name == "Deletion Test Snack"

        # Clean up test activity
        db.delete(remaining_activity)
        db.commit()

    finally:
        db.close()
