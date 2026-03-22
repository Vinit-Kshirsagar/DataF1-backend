from typing import Optional
from pydantic import BaseModel


class DriverResult(BaseModel):
    position: Optional[int] = None   # None for DNF/DNS
    driver_code: str
    driver_full_name: str
    team: str
    grid_position: Optional[int] = None
    points: float = 0.0
    status: str          # "Finished", "+1 Lap", "DNF", etc.
    fastest_lap: bool = False
    gap_to_leader: Optional[str] = None   # e.g. "+5.234s" or "+1 Lap"


class RaceResultsResponse(BaseModel):
    year: int
    round: int
    race_name: str
    session: str         # "R", "Q", "SQ"
    circuit: str
    date: str
    results: list[DriverResult]
    total_drivers: int
