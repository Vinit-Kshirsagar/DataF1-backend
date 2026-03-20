import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app
from app.schemas.telemetry import DataPoint, TelemetryResponse


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def make_telemetry_response() -> TelemetryResponse:
    return TelemetryResponse(
        year=2026,
        round=1,
        session="R",
        driver="VER",
        driver_full_name="Max Verstappen",
        team="Red Bull Racing",
        metric="throttle",
        metric_label="Throttle",
        metric_unit="%",
        data=[DataPoint(x=i * 10.0, y=float(80 + i)) for i in range(50)],
        total_laps=57,
        fastest_lap=82.456,
        summary="Shows aggressive throttle application through high-speed corners, indicating strong confidence in car balance.",
        partial=False,
    )


@pytest.mark.asyncio
async def test_get_telemetry_success(client):
    mock_response = make_telemetry_response()
    with patch(
        "app.routers.telemetry.telemetry_service.get_telemetry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        async with client as c:
            resp = await c.post("/telemetry/", json={
                "year": 2026,
                "round": 1,
                "session": "R",
                "driver": "VER",
                "metric": "throttle",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["driver"] == "VER"
        assert data["metric"] == "throttle"
        assert len(data["data"]) == 50
        assert "summary" in data
        assert data["summary"] != ""
        assert data["partial"] is False


@pytest.mark.asyncio
async def test_get_telemetry_missing_data(client):
    with patch(
        "app.routers.telemetry.telemetry_service.get_telemetry",
        new_callable=AsyncMock,
        side_effect=ValueError("No telemetry data available"),
    ):
        async with client as c:
            resp = await c.post("/telemetry/", json={
                "year": 2026,
                "round": 1,
                "session": "FP1",
                "driver": "VER",
                "metric": "throttle",
            })
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Data not available for selected parameters"


@pytest.mark.asyncio
async def test_get_telemetry_server_error(client):
    with patch(
        "app.routers.telemetry.telemetry_service.get_telemetry",
        new_callable=AsyncMock,
        side_effect=Exception("FastF1 network error"),
    ):
        async with client as c:
            resp = await c.post("/telemetry/", json={
                "year": 2026,
                "round": 1,
                "session": "R",
                "driver": "VER",
                "metric": "throttle",
            })
        assert resp.status_code == 503


@pytest.mark.asyncio
async def test_get_telemetry_invalid_payload(client):
    async with client as c:
        resp = await c.post("/telemetry/", json={
            "year": "not_a_year",
            "round": 1,
            "session": "R",
            "driver": "VER",
            "metric": "throttle",
        })
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_telemetry_summary_always_present(client):
    """Summary must always be in the response — even if partial."""
    mock_response = make_telemetry_response()
    mock_response.partial = True
    mock_response.summary = (
        "Telemetry data loaded for VER. Summary generation is temporarily unavailable."
    )
    with patch(
        "app.routers.telemetry.telemetry_service.get_telemetry",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        async with client as c:
            resp = await c.post("/telemetry/", json={
                "year": 2026,
                "round": 1,
                "session": "R",
                "driver": "VER",
                "metric": "throttle",
            })
        assert resp.status_code == 200
        data = resp.json()
        # Summary must never be empty — even fallback counts
        assert len(data["summary"]) > 0
        assert data["partial"] is True
