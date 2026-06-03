# f1pitwall/models/lap.py
from pydantic import BaseModel, Field
from datetime import timedelta
from enum import StrEnum

class TyreCompound(StrEnum):
    SOFT     = "SOFT"
    MEDIUM   = "MEDIUM"
    HARD     = "HARD"
    INTER    = "INTERMEDIATE"
    WET      = "WET"
    UNKNOWN  = "UNKNOWN"

class LapData(BaseModel):
    driver_number: str
    driver_code: str       # e.g. "VER", "HAM"
    lap_number: int
    lap_time_s: float | None          # seconds
    sector1_s: float | None
    sector2_s: float | None
    sector3_s: float | None
    compound: TyreCompound
    tyre_life: int                    # laps on this set
    stint_number: int
    is_valid: bool                    # FastF1 IsAccurate flag
    is_personal_best: bool
    position: int | None
    speed_trap: float | None          # km/h

    @property
    def is_usable(self) -> bool:
        """Lap is valid for analysis — not in/out laps, no track limits."""
        return self.is_valid and self.lap_time_s is not None and self.lap_time_s > 0