import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.redis_client import get_redis, close_redis

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs(settings.FASTF1_CACHE_DIR, exist_ok=True)
    await get_redis()

    # Fire-and-forget pre-cache — never blocks startup
    asyncio.create_task(_run_precache())

    yield

    # Shutdown
    await close_redis()


async def _run_precache():
    """Background pre-cache task — runs after server is fully started."""
    # Small delay to let server finish starting
    await asyncio.sleep(5)
    try:
        from app.services.precache_service import run_startup_precache
        await run_startup_precache()
    except Exception as e:
        logger.error(f"Pre-cache failed: {e}")


app = FastAPI(
    title="DataF1 API",
    description="Formula 1 telemetry interpretation and insight system",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/health", tags=["health"])
async def health_detail():
    redis = await get_redis()
    try:
        await redis.ping()
        redis_status = "ok"
    except Exception:
        redis_status = "unavailable"
    return {"status": "ok", "redis": redis_status}


@app.get("/warmup", tags=["health"])
async def warmup():
    """Manually trigger pre-cache. Call this after deploy."""
    asyncio.create_task(_run_precache())
    return {"status": "warming", "message": "Pre-cache started in background"}


@app.get("/cache-status", tags=["health"])
async def cache_status():
    """Show what's currently in Redis cache."""
    redis = await get_redis()
    keys = await redis.keys("*")
    telemetry_keys = [k.decode() for k in keys if b"telemetry" in k]
    race_keys = [k.decode() for k in keys if b"races" in k]
    result_keys = [k.decode() for k in keys if b"results" in k]
    return {
        "total_keys": len(keys),
        "telemetry_cached": len(telemetry_keys),
        "races_cached": len(race_keys),
        "results_cached": len(result_keys),
        "telemetry_keys": sorted(telemetry_keys)[:20],
    }


from app.routers import auth, races, telemetry, results  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(races.router, prefix="/races", tags=["races"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
app.include_router(results.router, prefix="/races", tags=["results"])
