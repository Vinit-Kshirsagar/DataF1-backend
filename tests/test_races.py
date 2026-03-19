import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.main import app
from app.schemas.races import (
    DriverResponse,
    MetricResponse,
    RaceResponse,
    SessionResponse,
)


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def make_races() -> list[RaceResponse]:
    return [
        RaceResponse(
            round=1,
            name="Bahrain Grand Prix",
            country="Bahrain",
            circuit="Sakhir",
            date="2024-03-02",
        ),
        RaceResponse(
            round=2,
            name="Saudi Arabian Grand Prix",
            country="Saudi Arabia",
            circuit="Jeddah",
            date="2024-03-09",
        ),
    ]


def make_sessions() -> list[SessionResponse]:
    return [
        SessionResponse(key="FP1", name="Practice 1"),
        SessionResponse(key="Q", name="Qualifying"),
        SessionResponse(key="R", name="Race"),
    ]


def make_drivers() -> list[DriverResponse]:
    return [
        DriverResponse(
            code="VER", full_name="Max Verstappen", team="Red Bull Racing", number="1"
        ),
        DriverResponse(
            code="HAM", full_name="Lewis Hamilton", team="Ferrari", number="44"
        ),
    ]


# ── Races ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_races_success(client):
    races = make_races()
    with patch(
        "app.routers.races.races_service.get_races",
        new_callable=AsyncMock,
        return_value=races,
    ):
        async with client as c:
            resp = await c.get("/races/2024")
        assert resp.status_code == 200
        data = resp.json()
        assert data["year"] == 2024
        assert len(data["races"]) == 2
        assert data["races"][0]["name"] == "Bahrain Grand Prix"


@pytest.mark.asyncio
async def test_list_races_invalid_year(client):
    async with client as c:
        resp = await c.get("/races/2010")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_list_races_fastf1_failure(client):
    with patch(
        "app.routers.races.races_service.get_races",
        new_callable=AsyncMock,
        side_effect=Exception("FastF1 unavailable"),
    ):
        async with client as c:
            resp = await c.get("/races/2024")
        assert resp.status_code == 503
        assert resp.json()["detail"] == "Data not available for selected parameters"


# ── Sessions ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_sessions_success(client):
    sessions = make_sessions()
    races = make_races()
    with (
        patch(
            "app.routers.races.races_service.get_sessions",
            new_callable=AsyncMock,
            return_value=sessions,
        ),
        patch(
            "app.routers.races.races_service.get_races",
            new_callable=AsyncMock,
            return_value=races,
        ),
    ):
        async with client as c:
            resp = await c.get("/races/2024/1/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["round"] == 1
        assert len(data["sessions"]) == 3
        assert data["sessions"][0]["key"] == "FP1"


# ── Drivers ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_drivers_success(client):
    drivers = make_drivers()
    with patch(
        "app.routers.races.races_service.get_drivers",
        new_callable=AsyncMock,
        return_value=drivers,
    ):
        async with client as c:
            resp = await c.get("/races/2024/1/sessions/R/drivers")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["drivers"]) == 2
        assert data["drivers"][0]["code"] == "VER"


# ── Metrics ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_metrics(client):
    async with client as c:
        resp = await c.get("/races/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["metrics"]) == 5
    keys = [m["key"] for m in data["metrics"]]
    assert "throttle" in keys
    assert "speed" in keys
    assert "lap_time" in keys
