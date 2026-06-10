# f1pitwall/strategy_simulator/safety_car.py
"""
Safety Car Luck Index
"""
import fastf1.core
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData


@dataclass
class SCEvent:
    lap_start: int
    lap_end: int
    event_type: str          # "SC" or "VSC"
    duration_laps: int


@dataclass
class DriverSCImpact:
    driver_code: str
    full_name: str
    luck_score: float
    events: list[dict] = field(default_factory=list)
    summary: str = ""


def extract_sc_events(session: fastf1.core.Session) -> list[SCEvent]:
    """
    Extract Safety Car and VSC periods from session track status data.

    FastF1 track_status codes:
      1 = AllClear
      2 = Yellow
      4 = SCDeployed
      5 = Red
      6 = VSCDeployed
      7 = VSCEnding
    """
    try:
        track_status = session.track_status
    except Exception:
        return []

    if track_status is None or track_status.empty:
        return []

    # Build a lap number → timestamp map from session laps
    try:
        all_laps = session.laps
        if all_laps is None or all_laps.empty:
            return []

        # Get one reference driver — use the one with most laps
        driver_lap_counts = all_laps.groupby("DriverNumber")["LapNumber"].count()
        ref_driver = driver_lap_counts.idxmax()
        ref_laps = all_laps[all_laps["DriverNumber"] == ref_driver].copy()
        ref_laps = ref_laps.dropna(subset=["LapStartTime"]).sort_values("LapNumber")

        # Build list of (lap_start_time, lap_number) tuples
        lap_timeline = list(zip(
            ref_laps["LapStartTime"].tolist(),
            ref_laps["LapNumber"].astype(int).tolist(),
        ))
    except Exception:
        return []

    def timestamp_to_lap(ts) -> int:
        """Find which lap was active at a given timestamp."""
        if pd.isna(ts):
            return 0
        best_lap = 1
        for lap_start, lap_num in lap_timeline:
            if pd.notna(lap_start) and lap_start <= ts:
                best_lap = lap_num
            else:
                break
        return best_lap

    sc_events: list[SCEvent] = []
    current_event: dict | None = None

    for _, row in track_status.iterrows():
        status = str(row.get("Status", "")).strip()
        timestamp = row.get("Time")

        if timestamp is None or pd.isna(timestamp):
            continue

        lap_num = timestamp_to_lap(timestamp)

        if status in ("4", "6"):
            # SC or VSC deployed
            event_type = "SC" if status == "4" else "VSC"
            if current_event is None:
                current_event = {
                    "type":      event_type,
                    "start_lap": lap_num,
                    "end_lap":   lap_num,
                }
            else:
                # Still under SC — update end lap
                current_event["end_lap"] = lap_num

        elif status in ("1", "2", "7"):
            # AllClear, Yellow, or VSCEnding — SC period over
            if current_event is not None:
                sc_events.append(SCEvent(
                    lap_start=current_event["start_lap"],
                    lap_end=current_event["end_lap"],
                    event_type=current_event["type"],
                    duration_laps=max(1, current_event["end_lap"] - current_event["start_lap"]),
                ))
                current_event = None

    # Close any event still open at end of race
    if current_event is not None:
        sc_events.append(SCEvent(
            lap_start=current_event["start_lap"],
            lap_end=current_event["end_lap"],
            event_type=current_event["type"],
            duration_laps=max(1, current_event["end_lap"] - current_event["start_lap"]),
        ))

    return sc_events


def _driver_pit_laps(driver: DriverSessionData) -> list[int]:
    """Get the lap numbers when this driver pitted."""
    pit_laps = []
    for stint in driver.stints[:-1]:
        if stint.laps:
            pit_laps.append(stint.laps[-1].lap_number)
    return pit_laps


def compute_sc_luck(
    driver: DriverSessionData,
    sc_events: list[SCEvent],
    pit_loss_s: float = 22.0,
) -> DriverSCImpact:
    """
    Compute the SC luck index for a single driver.

    Scoring:
      +50  pitted UNDER SC window (saved pit loss)
      +30  SC deployed within 3 laps BEFORE driver's next pit
      -30  SC deployed within 3 laps AFTER driver pitted (wasted fresh tyres)
    """
    pit_laps = _driver_pit_laps(driver)
    luck_score = 0.0
    events_log: list[dict] = []

    for sc in sc_events:
        for pit_lap in pit_laps:

            # Case 1: pitted UNDER SC window → very lucky
            if sc.lap_start <= pit_lap <= sc.lap_end:
                luck_score += 50
                events_log.append({
                    "type":    sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact":  "+50 (pitted under SC — saved pit loss)",
                })

            # Case 2: SC deployed 1–3 laps AFTER driver pitted → unlucky
            elif 1 <= (sc.lap_start - pit_lap) <= 3:
                luck_score -= 30
                events_log.append({
                    "type":    sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact":  f"-30 (SC {sc.lap_start - pit_lap} laps after pit — unlucky)",
                })

            # Case 3: SC ended 1–3 laps BEFORE driver due to pit → lucky
            elif 1 <= (pit_lap - sc.lap_end) <= 3:
                luck_score += 30
                events_log.append({
                    "type":    sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact":  f"+30 (SC ended {pit_lap - sc.lap_end} laps before pit — lucky)",
                })

    luck_score = float(np.clip(luck_score, -100, 100))

    if not events_log:
        summary = "No SC interaction — neutral"
    elif luck_score > 20:
        summary = f"Lucky (+{luck_score:.0f}) — benefited from SC timing"
    elif luck_score < -20:
        summary = f"Unlucky ({luck_score:.0f}) — hurt by SC timing"
    else:
        summary = f"Neutral ({luck_score:+.0f}) — SC had minimal impact"

    return DriverSCImpact(
        driver_code=driver.driver_code,
        full_name=driver.full_name,
        luck_score=luck_score,
        events=events_log,
        summary=summary,
    )


def compute_sc_luck_all(
    drivers: dict[str, DriverSessionData],
    session: fastf1.core.Session,
) -> dict[str, DriverSCImpact]:
    """Compute SC luck index for all drivers."""
    sc_events = extract_sc_events(session)

    if not sc_events:
        return {
            code: DriverSCImpact(
                driver_code=code,
                full_name=d.full_name,
                luck_score=0.0,
                summary="No SC/VSC in this race",
            )
            for code, d in drivers.items()
        }

    return {
        code: compute_sc_luck(driver, sc_events)
        for code, driver in drivers.items()
    }