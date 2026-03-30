import asyncio
import logging
from datetime import datetime, timezone

import fastf1

from app.config import settings
from app.redis_client import get_redis
from app.services import races_service, telemetry_service

logger = logging.getLogger(__name__)

# Top drivers to pre-cache telemetry for
PRIORITY_DRIVERS = ["VER", "NOR", "LEC", "HAM", "RUS"]
PRIORITY_METRICS = ["throttle", "speed", "lap_time"]


async def get_current_round(year: int) -> int:
    """Find the most recently completed race round."""
    try:
        schedule = fastf1.get_event_schedule(year, include_testing=False)
        today = datetime.now(timezone.utc)
        past = schedule[schedule["EventDate"] < today]
        if past.empty:
            return 1
        return int(past.iloc[-1]["RoundNumber"])
    except Exception as e:
        logger.warning(f"Could not determine current round: {e}")
        return 1


async def precache_race_schedule(year: int) -> None:
    """Pre-cache the full season schedule."""
    try:
        logger.info(f"Pre-caching {year} race schedule...")
        races = await races_service.get_races(year)
        logger.info(f"Cached {len(races)} races for {year}")
    except Exception as e:
        logger.error(f"Failed to pre-cache schedule: {e}")


async def precache_sessions(year: int, round_number: int) -> None:
    """Pre-cache sessions and drivers for a race weekend."""
    try:
        logger.info(f"Pre-caching sessions for {year} R{round_number}...")
        sessions = await races_service.get_sessions(year, round_number)

        for session in sessions:
            try:
                await races_service.get_drivers(year, round_number, session.key)
                logger.info(f"  Cached drivers for {session.name}")
            except Exception as e:
                logger.warning(f"  Failed drivers for {session.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to pre-cache sessions R{round_number}: {e}")


async def precache_telemetry(year: int, round_number: int) -> None:
    """Pre-cache telemetry for priority drivers in the Race session."""
    logger.info(f"Pre-caching telemetry for {year} R{round_number}...")

    for driver in PRIORITY_DRIVERS:
        for metric in PRIORITY_METRICS:
            try:
                cache_key = (
                    f"telemetry:{year}:{round_number}:R:{driver}:{metric}:0"
                )
                redis = await get_redis()
                cached = await redis.get(cache_key)
                if cached:
                    logger.info(f"  Already cached: {driver} {metric}")
                    continue

                logger.info(f"  Caching: {driver} {metric}...")
                await telemetry_service.get_telemetry(
                    year=year,
                    round_number=round_number,
                    session_key="R",
                    driver_code=driver,
                    metric=metric,
                    lap_number=0,
                )
                logger.info(f"  Done: {driver} {metric}")
                # Small delay to avoid hammering FastF1
                await asyncio.sleep(2)

            except Exception as e:
                logger.warning(f"  Failed {driver} {metric}: {e}")
                continue


async def run_startup_precache() -> None:
    """
    Full pre-cache run on startup.
    Runs in background — never blocks the server from starting.
    """
    year = datetime.now().year
    logger.info("=== Starting DataF1 startup pre-cache ===")

    # 1. Race schedule (fast — no FastF1 telemetry)
    await precache_race_schedule(year)

    # 2. Current round sessions + drivers
    current_round = await get_current_round(year)
    logger.info(f"Current round: {current_round}")

    await precache_sessions(year, current_round)

    # Also cache next round if it exists
    next_round = current_round + 1
    try:
        races = await races_service.get_races(year)
        if any(r.round == next_round for r in races):
            await precache_sessions(year, next_round)
    except Exception:
        pass

    # 3. Telemetry for current round top drivers (slowest — do last)
    await precache_telemetry(year, current_round)

    logger.info("=== Startup pre-cache complete ===")
