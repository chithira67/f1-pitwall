# f1pitwall/data_pipeline/cache.py
import json
import hashlib
from pathlib import Path
from f1pitwall.config import CACHE_DIR
from f1pitwall.models.driver import DriverSessionData

PARSED_DIR = CACHE_DIR / "parsed"
PARSED_DIR.mkdir(exist_ok=True)


def _cache_key(season: int, round_number: int, session_type: str) -> str:
    raw = f"{season}_{round_number}_{session_type}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def save_parsed_session(
    season: int,
    round_number: int,
    session_type: str,
    data: dict[str, DriverSessionData],
) -> Path:
    """Serialise parsed session to JSON for instant reload."""
    key = _cache_key(season, round_number, session_type)
    path = PARSED_DIR / f"{season}_r{round_number}_{session_type}_{key}.json"

    payload = {
        code: driver.model_dump(mode="json")
        for code, driver in data.items()
    }
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


def load_parsed_session(
    season: int,
    round_number: int,
    session_type: str,
) -> dict[str, DriverSessionData] | None:
    """Load previously parsed session from disk. Returns None if not cached."""
    key = _cache_key(season, round_number, session_type)
    path = PARSED_DIR / f"{season}_r{round_number}_{session_type}_{key}.json"

    if not path.exists():
        return None

    raw = json.loads(path.read_text())
    return {
        code: DriverSessionData.model_validate(payload)
        for code, payload in raw.items()
    }