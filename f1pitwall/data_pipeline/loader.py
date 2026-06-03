# f1pitwall/data_pipeline/loader.py
import fastf1
import fastf1.core
import pandas as pd
from rich.console import Console
from f1pitwall.config import CACHE_DIR, SESSION_TYPES
from f1pitwall.models.session import SessionInfo, SessionType

console = Console()

# Enable FastF1 cache — do this ONCE on import
fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_session(
    season: int,
    round_number: int,
    session_type: str = "R",
    load_telemetry: bool = True,
    load_weather: bool = True,
) -> fastf1.core.Session:
    """
    Load a FastF1 session with full telemetry.

    Args:
        season:          e.g. 2024
        round_number:    1-based round index (1 = Bahrain, etc.)
        session_type:    "R", "Q", "FP1", "FP2", "FP3", "S", "SQ"
        load_telemetry:  load car telemetry (speed, throttle, brake, gear)
        load_weather:    load weather data

    Returns:
        fastf1.core.Session — fully loaded, cached on disk after first call
    """
    if session_type not in SESSION_TYPES:
        raise ValueError(f"Unknown session type '{session_type}'. Valid: {list(SESSION_TYPES)}")

    console.print(
        f"[bold cyan]Loading[/] {season} Round {round_number} — "
        f"{SESSION_TYPES[session_type]}... (cached after first load)"
    )

    session = fastf1.get_session(season, round_number, session_type)
    session.load(
        telemetry=load_telemetry,
        weather=load_weather,
        messages=False,   # skip radio — not needed
    )

    console.print(f"[bold green]Loaded[/] {session.event['EventName']} {session_type}")
    return session


def get_session_info(session: fastf1.core.Session) -> SessionInfo:
    """Extract structured metadata from a loaded session."""
    return SessionInfo(
        season=session.event["EventDate"].year,
        round_number=int(session.event["RoundNumber"]),
        country=session.event["Country"],
        circuit=session.event["Location"],
        session_type=SessionType(session.name),
        date=session.event["EventDate"],
        total_laps=int(session.total_laps) if hasattr(session, "total_laps") else None,
    )


def list_rounds(season: int) -> pd.DataFrame:
    """Return the full event schedule for a season."""
    schedule = fastf1.get_event_schedule(season, include_testing=False)
    return schedule[["RoundNumber", "Country", "Location", "EventName", "EventDate"]]