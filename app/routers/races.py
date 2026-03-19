import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.races import (
    DriversListResponse,
    MetricsListResponse,
    RacesListResponse,
    SessionsListResponse,
)
from app.services import races_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/metrics", response_model=MetricsListResponse)
async def list_metrics():
    """Return available telemetry metrics."""
    return MetricsListResponse(metrics=races_service.get_metrics())


@router.get("/{year}", response_model=RacesListResponse)
async def list_races(year: int):
    """Return all races for a given season."""
    if year < 2018 or year > 2026:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Year must be between 2018 and 2026",
        )
    try:
        races = await races_service.get_races(year)
        return RacesListResponse(year=year, races=races)
    except Exception as e:
        logger.error(f"list_races error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )


@router.get(
    "/{year}/{round_number}/sessions",
    response_model=SessionsListResponse,
)
async def list_sessions(year: int, round_number: int):
    """Return available sessions for a race weekend."""
    try:
        sessions = await races_service.get_sessions(year, round_number)
        races = await races_service.get_races(year)
        race = next((r for r in races if r.round == round_number), None)
        race_name = race.name if race else f"Round {round_number}"

        return SessionsListResponse(
            year=year,
            round=round_number,
            race_name=race_name,
            sessions=sessions,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_sessions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )


@router.get(
    "/{year}/{round_number}/sessions/{session_key}/drivers",
    response_model=DriversListResponse,
)
async def list_drivers(year: int, round_number: int, session_key: str):
    """Return drivers who participated in a session."""
    try:
        drivers = await races_service.get_drivers(year, round_number, session_key)
        return DriversListResponse(
            year=year,
            round=round_number,
            session=session_key,
            drivers=drivers,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"list_drivers error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )
