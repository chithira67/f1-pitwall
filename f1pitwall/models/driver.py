# f1pitwall/models/driver.py
from pydantic import BaseModel
from .lap import LapData, TyreCompound

class StintSummary(BaseModel):
    stint_number: int
    compound: TyreCompound
    laps: list[LapData]
    avg_lap_time_s: float
    degradation_slope: float   # seconds lost per lap (from linear regression)

class DriverSessionData(BaseModel):
    driver_number: str
    driver_code: str
    full_name: str
    team: str
    grid_position: int | None
    finish_position: int | None
    laps: list[LapData]
    stints: list[StintSummary] = []
    fastest_lap_s: float | None = None

    @property
    def valid_laps(self) -> list[LapData]:
        return [l for l in self.laps if l.is_usable]

    @property
    def teammate_code(self) -> str | None:
        return None  # filled in by the pipeline after loading all drivers