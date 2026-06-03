# f1pitwall/models/session.py
from pydantic import BaseModel, Field
from datetime import datetime
from enum import StrEnum

class SessionType(StrEnum):
    FP1 = "FP1"
    FP2 = "FP2"
    FP3 = "FP3"
    QUALIFYING = "Q"
    SPRINT_QUALI = "SQ"
    SPRINT = "S"
    RACE = "R"

class SessionInfo(BaseModel):
    season: int
    round_number: int
    country: str
    circuit: str
    session_type: SessionType
    date: datetime
    total_laps: int | None = None

    @property
    def session_key(self) -> str:
        return f"{self.season}_{self.round_number}_{self.session_type}"