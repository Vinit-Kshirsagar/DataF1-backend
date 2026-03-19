import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock
import uuid
from datetime import datetime, timezone

from app.main import app


# ── Fixtures ─────────────────────────────────────────────────────────────────

def make_user(email: str = "test@example.com") -> MagicMock:
    user = MagicMock()
    user.id = uuid.uuid4()
    user.email = email
    user.hashed_password = "hashed"
    user.is_active = True
    user.created_at = datetime.now(timezone.utc)
    return user


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ── Register ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client):
    user = make_user()
    with (
        patch("app.routers.auth.get_user_by_email", new_callable=AsyncMock, return_value=None),
        patch("app.routers.auth.create_user", new_callable=AsyncMock, return_value=user),
    ):
        async with client as c:
            resp = await c.post("/auth/register", json={
                "email": "new@example.com",
                "password": "secret123"
            })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == user.email
        assert "password" not in data
        assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    user = make_user()
    with patch("app.routers.auth.get_user_by_email", new_callable=AsyncMock, return_value=user):
        async with client as c:
            resp = await c.post("/auth/register", json={
                "email": "existing@example.com",
                "password": "secret123"
            })
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_register_invalid_email(client):
    async with client as c:
        resp = await c.post("/auth/register", json={
            "email": "not-an-email",
            "password": "secret123"
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_short_password(client):
    async with client as c:
        resp = await c.post("/auth/register", json={
            "email": "test@example.com",
            "password": "abc"
        })
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client):
    user = make_user()
    with patch("app.routers.auth.authenticate_user", new_callable=AsyncMock, return_value=user):
        async with client as c:
            resp = await c.post("/auth/login", json={
                "email": "test@example.com",
                "password": "secret123"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_credentials(client):
    with patch("app.routers.auth.authenticate_user", new_callable=AsyncMock, return_value=None):
        async with client as c:
            resp = await c.post("/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid email or password"


# ── Refresh ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_invalid_token(client):
    async with client as c:
        resp = await c.post("/auth/refresh", json={"refresh_token": "invalid.token.here"})
    assert resp.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_no_token(client):
    async with client as c:
        resp = await c.get("/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_valid_token(client):
    from app.services.auth_service import create_access_token
    user = make_user()
    token = create_access_token(user.id)

    with patch("app.services.auth_service.get_user_by_id", new_callable=AsyncMock, return_value=user):
        async with client as c:
            resp = await c.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["email"] == user.email
