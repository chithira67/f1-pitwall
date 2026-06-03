# f1pitwall/config.py
from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
CACHE_DIR = ROOT_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# FastF1 cache size limit in GB (set None for unlimited)
CACHE_SIZE_LIMIT_GB: float | None = float(os.getenv("F1_CACHE_GB", "5"))

# Default season to work with
DEFAULT_SEASON: int = int(os.getenv("F1_SEASON", "2024"))

# Supported session types
SESSION_TYPES = {
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "Q":   "Qualifying",
    "SQ":  "Sprint Qualifying",
    "S":   "Sprint",
    "R":   "Race",
}