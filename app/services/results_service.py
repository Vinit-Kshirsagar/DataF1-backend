import json
import logging
import os
from typing import Optional

import fastf1
import numpy as np

from app.config import settings
from app.redis_client import get_redis
from app.schemas.results import DriverResult, RaceResultsResponse

logger = logging.getLogger(__name__)

os.makedirs(settings.FASTF1_CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(settings.FASTF1_CACHE_DIR)

RESULTS_TTL = 60 * 60 * 24  # 24 hours


def _safe_int(value) -> Optional[int]:
    try:
        f = float(value)
        if np.isnan(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _safe_float(value) -> float:
    try:
        f = float(value)
        return 0.0 if np.isnan(f) else f
    except (TypeError, ValueError):
        return 0.0


def _format_gap(value) -> Optional[str]:
    """Format gap to leader — e.g. '+5.234s' or '+1 Lap'."""
    try:
        if value is None:
            return None
        s = str(value).strip()
        if not s or s.lower() in ('nan', 'none', ''):
            return None
        # Already a string like '+1 Lap'
        if 'lap' in s.lower():
            return s
        # Timedelta
        if hasattr(value, 'total_seconds'):
            secs = value.total_seconds()
            if secs <= 0:
                return None
            return f"+{secs:.3f}s"
        return None
    except Exception:
        return None


async def get_results(
    year: int,
    round_number: int,
    session_key: str = "R",
) -> RaceResultsResponse:
    """
    Fetch race/qualifying results for a round.
    session_key: 'R' = Race, 'Q' = Qualifying, 'SQ' = Sprint Qualifying
    """
    cache_key = f"results:{year}:{round_number}:{session_key}"
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        logger.info(f"Cache HIT: {cache_key}")
        return RaceResultsResponse(**json.loads(cached))

    logger.info(f"Cache MISS: {cache_key}")

    session = fastf1.get_session(year, round_number, session_key)
    session.load(telemetry=False, weather=False, messages=False, laps=False)

    results_df = session.results
    event = session.event

    race_name = str(event.get("EventName", f"Round {round_number}"))
    circuit = str(event.get("Location", ""))
    date = str(event.get("EventDate", ""))[:10]

    # Find fastest lap setter (Race only)
    fastest_lap_driver = None
    if session_key == "R":
        try:
            session_laps = fastf1.get_session(year, round_number, session_key)
            session_laps.load(
                telemetry=False, weather=False, messages=False, laps=True
            )
            fl = session_laps.laps.pick_fastest()
            fastest_lap_driver = str(fl.get("Driver", ""))
        except Exception:
            pass

    driver_results: list[DriverResult] = []

    for _, row in results_df.iterrows():
        position = _safe_int(row.get("Position"))
        code = str(row.get("Abbreviation", "???"))
        full_name = str(row.get("FullName", code))
        team = str(row.get("TeamName", "Unknown"))
        grid = _safe_int(row.get("GridPosition"))
        points = _safe_float(row.get("Points"))
        status = str(row.get("Status", "Unknown"))

        # Gap — only meaningful for Race
        gap = None
        if session_key == "R" and position and position > 1:
            gap = _format_gap(row.get("Time"))

        driver_results.append(DriverResult(
            position=position,
            driver_code=code,
            driver_full_name=full_name,
            team=team,
            grid_position=grid,
            points=points,
            status=status,
            fastest_lap=(code == fastest_lap_driver),
            gap_to_leader=gap,
        ))

    # Sort by position (DNFs go to bottom)
    driver_results.sort(key=lambda x: (x.position is None, x.position or 99))

    response = RaceResultsResponse(
        year=year,
        round=round_number,
        race_name=race_name,
        session=session_key,
        circuit=circuit,
        date=date,
        results=driver_results,
        total_drivers=len(driver_results),
    )

    try:
        await redis.setex(
            cache_key, RESULTS_TTL, json.dumps(response.model_dump())
        )
    except Exception as e:
        logger.warning(f"Failed to cache results: {e}")

    return response
