from typing import Optional
from pydantic import BaseModel


# ── Request ───────────────────────────────────────────────────────────────────

class TelemetryRequest(BaseModel):
    year: int
    round: int
    session: str
    driver: str
    metric: str
    lap_number: int = 0  # 0 = fastest lap (default)


class ComparisonRequest(BaseModel):
    year: int
    round: int
    session: str
    driver1: str
    driver2: str
    metric: str
    lap_number: int = 0  # 0 = fastest lap for both drivers


# ── Response ──────────────────────────────────────────────────────────────────

class DataPoint(BaseModel):
    x: float
    y: float


class LapInfo(BaseModel):
    lap_number: int
    lap_time: Optional[float] = None  # seconds
    is_fastest: bool = False


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
    fastest_lap: Optional[float] = None
    selected_lap: int = 0            # 0 = fastest, else specific lap number
    laps: list[LapInfo] = []         # all laps for the picker sheet
    summary: str
    partial: bool = False


class ComparisonDriver(BaseModel):
    driver: str
    driver_full_name: str
    team: str
    data: list[DataPoint]
    fastest_lap: Optional[float] = None
    selected_lap: int = 0


class ComparisonResponse(BaseModel):
    year: int
    round: int
    session: str
    metric: str
    metric_label: str
    metric_unit: str
    driver1: ComparisonDriver
    driver2: ComparisonDriver
    summary: str
