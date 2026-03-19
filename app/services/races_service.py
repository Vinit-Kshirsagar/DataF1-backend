import json
import logging
import os
from typing import Any

import fastf1

from app.config import settings
from app.redis_client import get_redis
from app.schemas.races import (
    DriverResponse,
    MetricResponse,
    RaceResponse,
    SessionResponse,
)

logger = logging.getLogger(__name__)

# FastF1 cache setup
os.makedirs(settings.FASTF1_CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(settings.FASTF1_CACHE_DIR)

# Redis TTL
RACES_TTL = 60 * 60 * 24  # 24 hours — race calendar doesn't change
SESSIONS_TTL = 60 * 60 * 6  # 6 hours
DRIVERS_TTL = 60 * 60 * 6   # 6 hours

# Fixed metrics — these never change
AVAILABLE_METRICS: list[MetricResponse] = [
    MetricResponse(key="throttle", label="Throttle", unit="%"),
    MetricResponse(key="brake", label="Brake", unit="%"),
    MetricResponse(key="speed", label="Speed", unit="km/h"),
    MetricResponse(key="lap_time", label="Lap Time", unit="s"),
    MetricResponse(key="top_speed", label="Top Speed", unit="km/h"),
]


async def get_races(year: int) -> list[RaceResponse]:
    """Return all races for a given season, Redis-cached."""
    cache_key = f"races:{year}"
    redis = await get_redis()

    # Cache hit
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [RaceResponse(**r) for r in data]

    # Cache miss — fetch from FastF1
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        races: list[RaceResponse] = []

        for _, row in schedule.iterrows():
            try:
                races.append(
                    RaceResponse(
                        round=int(row["RoundNumber"]),
                        name=str(row["EventName"]),
                        country=str(row["Country"]),
                        circuit=str(row["Location"]),
                        date=str(row["EventDate"].date()),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping race row: {e}")
                continue

        # Store in Redis
        await redis.setex(
            cache_key,
            RACES_TTL,
            json.dumps([r.model_dump() for r in races]),
        )
        return races

    except Exception as e:
        logger.error(f"FastF1 get_races failed for year {year}: {e}")
        raise


async def get_sessions(year: int, round_number: int) -> list[SessionResponse]:
    """Return available sessions for a race weekend, Redis-cached."""
    cache_key = f"sessions:{year}:{round_number}"
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [SessionResponse(**s) for s in data]

    try:
        event = fastf1.get_event(year, round_number)
        sessions: list[SessionResponse] = []

        session_map = {
            "Practice 1": "FP1",
            "Practice 2": "FP2",
            "Practice 3": "FP3",
            "Sprint Shootout": "SS",
            "Sprint": "S",
            "Qualifying": "Q",
            "Race": "R",
        }

        for name, key in session_map.items():
            try:
                # Check if session exists by attempting to access it
                session_date = getattr(event, name.replace(" ", ""), None)
                if session_date is not None:
                    sessions.append(SessionResponse(key=key, name=name))
            except Exception:
                continue

        # If nothing found, return standard set
        if not sessions:
            sessions = [
                SessionResponse(key="FP1", name="Practice 1"),
                SessionResponse(key="FP2", name="Practice 2"),
                SessionResponse(key="FP3", name="Practice 3"),
                SessionResponse(key="Q", name="Qualifying"),
                SessionResponse(key="R", name="Race"),
            ]

        await redis.setex(
            cache_key,
            SESSIONS_TTL,
            json.dumps([s.model_dump() for s in sessions]),
        )
        return sessions

    except Exception as e:
        logger.error(
            f"FastF1 get_sessions failed for {year} round {round_number}: {e}"
        )
        raise


async def get_drivers(
    year: int, round_number: int, session_key: str
) -> list[DriverResponse]:
    """Return drivers who participated in a session, Redis-cached."""
    cache_key = f"drivers:{year}:{round_number}:{session_key}"
    redis = await get_redis()

    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        return [DriverResponse(**d) for d in data]

    try:
        session = fastf1.get_session(year, round_number, session_key)
        session.load(telemetry=False, weather=False, messages=False)

        drivers: list[DriverResponse] = []
        results = session.results

        for _, row in results.iterrows():
            try:
                drivers.append(
                    DriverResponse(
                        code=str(row.get("Abbreviation", "UNK")),
                        full_name=str(
                            row.get("FullName", row.get("Abbreviation", "Unknown"))
                        ),
                        team=str(row.get("TeamName", "Unknown")),
                        number=str(row.get("DriverNumber", "")),
                    )
                )
            except Exception as e:
                logger.warning(f"Skipping driver row: {e}")
                continue

        await redis.setex(
            cache_key,
            DRIVERS_TTL,
            json.dumps([d.model_dump() for d in drivers]),
        )
        return drivers

    except Exception as e:
        logger.error(
            f"FastF1 get_drivers failed for "
            f"{year} round {round_number} {session_key}: {e}"
        )
        raise


def get_metrics() -> list[MetricResponse]:
    """Return available telemetry metrics — static, no FastF1 call needed."""
    return AVAILABLE_METRICS
