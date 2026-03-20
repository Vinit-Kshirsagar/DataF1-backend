import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.telemetry import TelemetryRequest, TelemetryResponse
from app.services import telemetry_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=TelemetryResponse)
async def get_telemetry(payload: TelemetryRequest):
    """
    Fetch telemetry data for a driver + metric combination.
    Returns graph data points and an AI-generated insight summary.
    Cache-first: Redis hit returns in < 1s. Miss fetches from FastF1 (5-15s first time).
    """
    try:
        return await telemetry_service.get_telemetry(
            year=payload.year,
            round_number=payload.round,
            session_key=payload.session,
            driver_code=payload.driver,
            metric=payload.metric,
        )
    except ValueError as e:
        # Missing data — expected for some sessions/drivers
        logger.warning(f"Telemetry not available: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not available for selected parameters",
        )
    except Exception as e:
        logger.error(f"Telemetry endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )
