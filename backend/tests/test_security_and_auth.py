"""Test Suite: Security, Authorization Guards, and Credential Privacy.

Covers:
5. Authorization:
   - Unauthenticated access (missing/invalid token) returns 401 UNAUTHORIZED.
   - Non-admin members attempting admin actions (restock, POST/PATCH/DELETE /snacks)
     return 403 FORBIDDEN.
   - Admin is authorized to perform all pantry operations.
6. Auth Security:
   - Wrong password and wrong email return identical generic 401 error message.
   - `password_hash` is strictly excluded from all API response payloads.
   - Passwords stored in the PostgreSQL database are verified to be salted bcrypt hashes.
"""

from typing import Dict
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Snack, SnackCategory, User
from app.security import verify_password


def test_authorization_role_guards(
    client: TestClient,
    db_session: Session,
    admin_headers: Dict[str, str],
    member_headers: Dict[str, str],
):
    """
    Test 5: Authorization Guards.
    
    Verifies that:
    1. Protected routes reject requests with no token with 401 UNAUTHORIZED.
    2. Member role is forbidden from admin routes (restock, POST, PATCH, DELETE /snacks)
       with 403 FORBIDDEN.
    3. Admin role is permitted across all endpoints.
    """
    # 1. Arrange: Create a baseline snack
    snack = Snack(
        name="Guards Test Pretzel",
        category=SnackCategory.SAVOURY,
        quantity=10,
        low_stock_threshold=3,
    )
    db_session.add(snack)
    db_session.commit()
    db_session.refresh(snack)
    snack_id = snack.id

    # 2. Check 401 UNAUTHORIZED on unauthenticated requests
    unauth_endpoints = [
        ("GET", "/auth/me", None),
        ("GET", "/snacks", None),
        ("POST", "/snacks", {"name": "X", "category": "sweet", "quantity": 1, "low_stock_threshold": 1}),
        ("POST", f"/snacks/{snack_id}/consume", {"amount": 1}),
        ("POST", f"/snacks/{snack_id}/restock", {"amount": 1}),
        ("PATCH", f"/snacks/{snack_id}", {"name": "New Name"}),
        ("DELETE", f"/snacks/{snack_id}", None),
    ]

    for method, path, payload in unauth_endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json=payload)
        elif method == "PATCH":
            res = client.patch(path, json=payload)
        elif method == "DELETE":
            res = client.delete(path)
        
        assert res.status_code == 401, f"{method} {path} without token returned {res.status_code}"
        assert res.json()["error"]["code"] == "UNAUTHORIZED"

    # 3. Check 403 FORBIDDEN when member calls admin routes
    admin_routes_for_member = [
        ("POST", "/snacks", {"name": "Member Illegal Snack", "category": "sweet", "quantity": 1, "low_stock_threshold": 1}),
        ("POST", f"/snacks/{snack_id}/restock", {"amount": 5}),
        ("PATCH", f"/snacks/{snack_id}", {"name": "Hacked Name"}),
        ("DELETE", f"/snacks/{snack_id}", None),
    ]

    for method, path, payload in admin_routes_for_member:
        if method == "POST":
            res = client.post(path, json=payload, headers=member_headers)
        elif method == "PATCH":
            res = client.patch(path, json=payload, headers=member_headers)
        elif method == "DELETE":
            res = client.delete(path, headers=member_headers)

        assert res.status_code == 403, f"{method} {path} with member role returned {res.status_code}"
        assert res.json()["error"]["code"] == "FORBIDDEN"

    # 4. Check admin is allowed on all admin routes
    # Admin POST /snacks
    res_create = client.post(
        "/snacks",
        json={"name": "Admin Approved Popcorn", "category": "savoury", "quantity": 12, "low_stock_threshold": 4},
        headers=admin_headers,
    )
    assert res_create.status_code == 201
    created_id = res_create.json()["id"]

    # Admin POST /snacks/{id}/restock
    res_restock = client.post(
        f"/snacks/{created_id}/restock",
        json={"amount": 5},
        headers=admin_headers,
    )
    assert res_restock.status_code == 200
    assert res_restock.json()["quantity"] == 17

    # Admin PATCH /snacks/{id}
    res_patch = client.patch(
        f"/snacks/{created_id}",
        json={"name": "Admin Approved Butter Popcorn"},
        headers=admin_headers,
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Admin Approved Butter Popcorn"

    # Admin DELETE /snacks/{id}
    res_delete = client.delete(
        f"/snacks/{created_id}",
        headers=admin_headers,
    )
    assert res_delete.status_code == 204


def test_auth_credentials_and_password_privacy(
    client: TestClient,
    db_session: Session,
    admin_user: User,
    member_user: User,
    admin_headers: Dict[str, str],
):
    """
    Test 6: Authentication Security, Timing Attack Resistance & Password Privacy.
    
    Verifies that:
    1. Incorrect password returns 401 UNAUTHORIZED.
    2. Non-existent email returns 401 UNAUTHORIZED with the exact same error message,
       preventing username enumeration.
    3. `password_hash` is NEVER present in /auth/login or /auth/me responses.
    4. Database stores valid bcrypt hashes (starts with $2b$), never plain text.
    """
    # 1. Non-existent email vs Wrong password produce identical 401 errors
    res_wrong_email = client.post(
        "/auth/login",
        json={"email": "nonexistent_hacker@snack.local", "password": "AnyPassword123"},
    )
    assert res_wrong_email.status_code == 401
    body_wrong_email = res_wrong_email.json()

    res_wrong_password = client.post(
        "/auth/login",
        json={"email": admin_user.email, "password": "WrongPassword@999"},
    )
    assert res_wrong_password.status_code == 401
    body_wrong_password = res_wrong_password.json()

    # Invariant: identical envelopes prevent account enumeration
    assert body_wrong_email["error"]["code"] == "UNAUTHORIZED"
    assert body_wrong_password["error"]["code"] == "UNAUTHORIZED"
    assert body_wrong_email["error"]["message"] == body_wrong_password["error"]["message"]
    assert body_wrong_email["error"]["message"] == "Invalid email or password"

    # 2. Successful login never leaks password_hash
    res_login = client.post(
        "/auth/login",
        json={"email": admin_user.email, "password": "Admin@123"},
    )
    assert res_login.status_code == 200
    login_data = res_login.json()
    assert "access_token" in login_data
    assert "user" in login_data
    assert "password_hash" not in login_data["user"]
    assert "password" not in login_data["user"]

    # 3. GET /auth/me never leaks password_hash
    res_me = client.get("/auth/me", headers=admin_headers)
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert "password_hash" not in me_data
    assert "password" not in me_data
    assert me_data["email"] == admin_user.email

    # 4. Passwords in PostgreSQL are salted bcrypt hashes
    db_user = db_session.get(User, admin_user.id)
    assert db_user is not None
    assert db_user.password_hash != "Admin@123"
    assert db_user.password_hash.startswith("$2b$")
    assert verify_password("Admin@123", db_user.password_hash) is True
    assert verify_password("Wrong@123", db_user.password_hash) is False
