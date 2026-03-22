import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.results import RaceResultsResponse
from app.services import results_service

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_SESSIONS = {"R", "Q", "SQ", "FP1", "FP2", "FP3"}


@router.get("/{year}/{round}/results", response_model=RaceResultsResponse)
async def get_race_results(
    year: int,
    round: int,
    session: str = "R",
):
    """
    Fetch results for a race weekend session.
    session: R (Race), Q (Qualifying), SQ (Sprint Qualifying)
    Defaults to Race results.
    """
    if year < 2018 or year > 2026:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Year must be between 2018 and 2026",
        )
    if session not in VALID_SESSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session must be one of: {', '.join(VALID_SESSIONS)}",
        )
    try:
        return await results_service.get_results(
            year=year,
            round_number=round,
            session_key=session,
        )
    except Exception as e:
        logger.error(f"Results error {year} R{round} {session}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Data not available for selected parameters",
        )
