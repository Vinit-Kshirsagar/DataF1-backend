from pydantic import BaseModel
from typing import Optional


# ── Races ────────────────────────────────────────────────────────────────────

class RaceResponse(BaseModel):
    round: int
    name: str
    country: str
    circuit: str
    date: str  # ISO format YYYY-MM-DD


class RacesListResponse(BaseModel):
    year: int
    races: list[RaceResponse]


# ── Sessions ─────────────────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    key: str   # e.g. "R", "Q", "FP1"
    name: str  # e.g. "Race", "Qualifying", "Practice 1"


class SessionsListResponse(BaseModel):
    year: int
    round: int
    race_name: str
    sessions: list[SessionResponse]


# ── Drivers ──────────────────────────────────────────────────────────────────

class DriverResponse(BaseModel):
    code: str           # e.g. "VER"
    full_name: str      # e.g. "Max Verstappen"
    team: str           # e.g. "Red Bull Racing"
    number: Optional[str] = None  # e.g. "1"


class DriversListResponse(BaseModel):
    year: int
    round: int
    session: str
    drivers: list[DriverResponse]


# ── Metrics ──────────────────────────────────────────────────────────────────

class MetricResponse(BaseModel):
    key: str    # e.g. "throttle"
    label: str  # e.g. "Throttle"
    unit: str   # e.g. "%", "km/h", "s"


class MetricsListResponse(BaseModel):
    metrics: list[MetricResponse]
