from typing import Optional
from pydantic import BaseModel


# ── Request ───────────────────────────────────────────────────────────────────

class TelemetryRequest(BaseModel):
    year: int
    round: int
    session: str      # e.g. "R", "Q", "FP1"
    driver: str       # e.g. "VER"
    metric: str       # e.g. "throttle"


# ── Response ──────────────────────────────────────────────────────────────────

class DataPoint(BaseModel):
    x: float   # lap number or distance (metres)
    y: float   # metric value


class TelemetryResponse(BaseModel):
    year: int
    round: int
    session: str
    driver: str
    driver_full_name: str
    team: str
    metric: str
    metric_label: str
    metric_unit: str
    data: list[DataPoint]
    total_laps: int
    fastest_lap: Optional[float] = None   # seconds
    summary: str                           # AI-generated insight
    partial: bool = False                  # True if some laps were missing
