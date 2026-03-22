import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.telemetry import (
    ComparisonRequest,
    ComparisonResponse,
    TelemetryRequest,
    TelemetryResponse,
)
from app.services import telemetry_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=TelemetryResponse)
async def get_telemetry(payload: TelemetryRequest):
    """
    Fetch telemetry for a driver + metric + optional specific lap.
    lap_number=0 (default) returns fastest lap.
    Response includes all lap infos for the lap picker sheet.
    """
    try:
        return await telemetry_service.get_telemetry(
            year=payload.year,
            round_number=payload.round,
            session_key=payload.session,
            driver_code=payload.driver,
            metric=payload.metric,
            lap_number=payload.lap_number,
        )
    except ValueError as e:
        logger.warning(f"Telemetry not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not available for selected parameters",
        )
    except Exception as e:
        logger.error(f"Telemetry error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )


@router.post("/compare", response_model=ComparisonResponse)
async def get_comparison(payload: ComparisonRequest):
    """
    Fetch telemetry for two drivers on the same metric.
    Returns both data sets and a combined AI summary.
    """
    if payload.driver1 == payload.driver2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select two different drivers to compare",
        )
    try:
        return await telemetry_service.get_comparison(
            year=payload.year,
            round_number=payload.round,
            session_key=payload.session,
            driver1_code=payload.driver1,
            driver2_code=payload.driver2,
            metric=payload.metric,
            lap_number=payload.lap_number,
        )
    except ValueError as e:
        logger.warning(f"Comparison not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not available for selected parameters",
        )
    except Exception as e:
        logger.error(f"Comparison error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )
