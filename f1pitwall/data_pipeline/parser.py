# f1pitwall/data_pipeline/parser.py
import numpy as np
import pandas as pd
import fastf1.core
from scipy import stats  # pip install scipy — add to pyproject.toml
from rich.console import Console

from f1pitwall.models.lap import LapData, TyreCompound
from f1pitwall.models.driver import DriverSessionData, StintSummary

console = Console()

COMPOUND_MAP = {
    "SOFT": TyreCompound.SOFT,
    "MEDIUM": TyreCompound.MEDIUM,
    "HARD": TyreCompound.HARD,
    "INTERMEDIATE": TyreCompound.INTER,
    "WET": TyreCompound.WET,
}


def _parse_timedelta(td) -> float | None:
    """Convert pandas Timedelta to seconds float, handling NaT."""
    if pd.isna(td):
        return None
    try:
        return td.total_seconds()
    except Exception:
        return None


def parse_driver_laps(
    session: fastf1.core.Session,
    driver_code: str,
) -> DriverSessionData:
    """
    Parse all lap data for a single driver in a session.

    Args:
        session:     loaded FastF1 session
        driver_code: three-letter code, e.g. "VER"

    Returns:
        DriverSessionData with all laps and stint summaries
    """
    driver_laps: pd.DataFrame = session.laps.pick_drivers(driver_code)

    if driver_laps.empty:
        raise ValueError(f"No laps found for driver '{driver_code}' in this session.")

    # Driver metadata
    drv_info = session.get_driver(driver_code)
    full_name = f"{drv_info['FirstName']} {drv_info['LastName']}"
    team = drv_info["TeamName"]
    driver_number = str(drv_info["DriverNumber"])

    # Grid/finish positions
    results = session.results
    grid_pos = finish_pos = None
    if results is not None and not results.empty:
        row = results[results["Abbreviation"] == driver_code]
        if not row.empty:
            grid_pos = int(row["GridPosition"].iloc[0]) if pd.notna(row["GridPosition"].iloc[0]) else None
            finish_pos = int(row["Position"].iloc[0]) if pd.notna(row["Position"].iloc[0]) else None

    # Build lap objects
    laps: list[LapData] = []
    for _, lap in driver_laps.iterrows():
        compound_raw = str(lap.get("Compound", "UNKNOWN")).upper()
        compound = COMPOUND_MAP.get(compound_raw, TyreCompound.UNKNOWN)

        lap_obj = LapData(
            driver_number=driver_number,
            driver_code=driver_code,
            lap_number=int(lap["LapNumber"]),
            lap_time_s=_parse_timedelta(lap.get("LapTime")),
            sector1_s=_parse_timedelta(lap.get("Sector1Time")),
            sector2_s=_parse_timedelta(lap.get("Sector2Time")),
            sector3_s=_parse_timedelta(lap.get("Sector3Time")),
            compound=compound,
            tyre_life=int(lap.get("TyreLife", 0) or 0),
            stint_number=int(lap.get("Stint", 1) or 1),
            is_valid=bool(lap.get("IsAccurate", False)),
            is_personal_best=bool(lap.get("IsPersonalBest", False)),
            position=int(lap["Position"]) if pd.notna(lap.get("Position")) else None,
            speed_trap=float(lap["SpeedST"]) if pd.notna(lap.get("SpeedST")) else None,
        )
        laps.append(lap_obj)

    # Build stint summaries
    stints = _build_stints(laps)

    fastest_lap = min(
        (l.lap_time_s for l in laps if l.is_usable),
        default=None
    )

    return DriverSessionData(
        driver_number=driver_number,
        driver_code=driver_code,
        full_name=full_name,
        team=team,
        grid_position=grid_pos,
        finish_position=finish_pos,
        laps=laps,
        stints=stints,
        fastest_lap_s=fastest_lap,
    )


def _build_stints(laps: list[LapData]) -> list[StintSummary]:
    """Group laps into stints and compute degradation slope per stint."""
    from collections import defaultdict

    stint_groups: dict[int, list[LapData]] = defaultdict(list)
    for lap in laps:
        if lap.is_usable:
            stint_groups[lap.stint_number].append(lap)

    stints: list[StintSummary] = []
    for stint_num, stint_laps in sorted(stint_groups.items()):
        if len(stint_laps) < 2:
            slope = 0.0
        else:
            tyre_ages = [l.tyre_life for l in stint_laps]
            lap_times = [l.lap_time_s for l in stint_laps]  # type: ignore
            slope, _, _, _, _ = stats.linregress(tyre_ages, lap_times)

        avg_time = float(np.mean([l.lap_time_s for l in stint_laps]))  # type: ignore

        stints.append(StintSummary(
            stint_number=stint_num,
            compound=stint_laps[0].compound,
            laps=stint_laps,
            avg_lap_time_s=avg_time,
            degradation_slope=float(slope),
        ))

    return stints


def parse_all_drivers(session: fastf1.core.Session) -> dict[str, DriverSessionData]:
    """
    Parse all drivers in a session.

    Returns:
        dict mapping driver_code → DriverSessionData
    """
    drivers = session.drivers  # list of driver numbers
    results: dict[str, DriverSessionData] = {}

    for drv_num in drivers:
        try:
            code = session.get_driver(drv_num)["Abbreviation"]
            data = parse_driver_laps(session, code)
            results[code] = data
            console.print(f"  [dim]Parsed[/] {code} — {len(data.valid_laps)} valid laps")
        except Exception as e:
            console.print(f"  [yellow]Skipped[/] driver {drv_num}: {e}")

    return results