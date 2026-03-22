import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.redis_client import get_redis, close_redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.FASTF1_CACHE_DIR, exist_ok=True)
    await get_redis()
    yield
    await close_redis()


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


from app.routers import auth, races, telemetry, results  # noqa: E402

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(races.router, prefix="/races", tags=["races"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["telemetry"])
app.include_router(results.router, prefix="/races", tags=["results"])
