"""Test suite for authentication, authorization, security, and error envelopes."""

import pytest
from fastapi.testclient import TestClient

from app.deps import require_admin
from app.errors import ForbiddenError
from app.main import app
from app.models import User, UserRole
from app.security import hash_password, verify_password

client = TestClient(app)


def test_bcrypt_hashing_and_verification():
    """Verify direct bcrypt hashing and constant-time password verification."""
    password = "MySecurePassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_login_success_admin():
    """Verify login with demo admin credentials returns JWT and safe user object."""
    response = client.post(
        "/auth/login",
        json={"email": "admin@snack.local", "password": "Admin@123"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user" in data
    assert data["user"]["email"] == "admin@snack.local"
    assert data["user"]["role"] == "admin"
    assert "password_hash" not in data["user"]
    assert "password" not in data["user"]


def test_login_success_member():
    """Verify login with demo member credentials returns JWT and safe user object."""
    response = client.post(
        "/auth/login",
        json={"email": "member@snack.local", "password": "Member@123"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "member@snack.local"
    assert data["user"]["role"] == "member"
    assert "password_hash" not in data["user"]


def test_login_failure_identical_error_messages():
    """Verify wrong email and wrong password yield identical generic 401 error message."""
    res1 = client.post(
        "/auth/login",
        json={"email": "nonexistent@snack.local", "password": "Admin@123"},
    )
    assert res1.status_code == 401
    body1 = res1.json()
    assert body1["error"]["code"] == "UNAUTHORIZED"
    assert body1["error"]["message"] == "Invalid email or password"

    res2 = client.post(
        "/auth/login",
        json={"email": "admin@snack.local", "password": "WrongPassword@999"},
    )
    assert res2.status_code == 401
    body2 = res2.json()
    assert body2["error"]["code"] == "UNAUTHORIZED"
    assert body2["error"]["message"] == "Invalid email or password"

    assert body1 == body2


def test_login_validation_error_with_details():
    """Verify schema validation error (422) produces standardized envelope with 'details' array."""
    response = client.post(
        "/auth/login",
        json={"email": "not-an-email", "password": ""},
    )
    assert response.status_code == 422
    body = response.json()

    assert "error" in body
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in body["error"]
    assert isinstance(body["error"]["details"], list)
    assert len(body["error"]["details"]) >= 1


def test_get_me_success():
    """Verify /auth/me returns current user when valid Bearer token is provided."""
    login_res = client.post(
        "/auth/login",
        json={"email": "member@snack.local", "password": "Member@123"},
    )
    token = login_res.json()["access_token"]

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    user_data = response.json()

    assert user_data["email"] == "member@snack.local"
    assert user_data["role"] == "member"
    assert "password_hash" not in user_data


def test_get_me_missing_token():
    """Verify /auth/me rejects requests without token with 401 UNAUTHORIZED."""
    response = client.get("/auth/me")
    assert response.status_code == 401
    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Authentication token missing"


def test_get_me_tampered_token():
    """Verify /auth/me rejects requests with corrupt or tampered token."""
    response = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer totally-corrupted-token.payload.signature"},
    )
    assert response.status_code == 401
    body = response.json()

    assert body["error"]["code"] == "UNAUTHORIZED"
    assert body["error"]["message"] == "Invalid authentication token"


def test_require_admin_guard():
    """Verify require_admin allows admins and raises 403 Forbidden for members."""
    admin_user = User(
        id=1,
        name="Admin",
        email="admin@snack.local",
        password_hash="x",
        role=UserRole.ADMIN,
    )
    member_user = User(
        id=2,
        name="Member",
        email="member@snack.local",
        password_hash="x",
        role=UserRole.MEMBER,
    )

    assert require_admin(admin_user) == admin_user

    with pytest.raises(ForbiddenError) as exc_info:
        require_admin(member_user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "FORBIDDEN"
