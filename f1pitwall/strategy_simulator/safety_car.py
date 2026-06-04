# f1pitwall/strategy_simulator/safety_car.py
"""
Safety Car Luck Index

Measures how much a driver benefited or was hurt by SC/VSC timing
relative to their pit stop status.

Logic:
  - If SC comes out AFTER driver pitted recently → unlucky (lost free stop)
  - If SC comes out BEFORE driver pits → lucky (free stop available)
  - If driver pits UNDER SC → very lucky (minimal pit loss)
"""
import fastf1.core
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData


@dataclass
class SCEvent:
    """A single safety car or VSC deployment."""
    lap_start: int
    lap_end: int
    event_type: str          # "SC" or "VSC"
    duration_laps: int


@dataclass
class DriverSCImpact:
    """How SC events affected a specific driver."""
    driver_code: str
    full_name: str
    luck_score: float        # -100 (very unlucky) to +100 (very lucky)
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

    sc_events: list[SCEvent] = []
    current_event: dict | None = None

    for _, row in track_status.iterrows():
        status = str(row.get("Status", ""))
        # Map status to lap number via session laps
        try:
            timestamp = row.get("Time")
            if timestamp is None:
                continue
            # Find closest lap number to this timestamp
            lap_num = _timestamp_to_lap(session, timestamp)
        except Exception:
            continue

        if status in ("4", "6"):  # SC or VSC deployed
            event_type = "SC" if status == "4" else "VSC"
            if current_event is None:
                current_event = {
                    "type": event_type,
                    "start_lap": lap_num,
                    "end_lap": lap_num,
                }
            else:
                current_event["end_lap"] = lap_num

        elif status == "1" and current_event is not None:
            # AllClear — SC period ended
            sc_events.append(SCEvent(
                lap_start=current_event["start_lap"],
                lap_end=current_event["end_lap"],
                event_type=current_event["type"],
                duration_laps=max(1, current_event["end_lap"] - current_event["start_lap"]),
            ))
            current_event = None

    # Close any open event at end of race
    if current_event is not None:
        sc_events.append(SCEvent(
            lap_start=current_event["start_lap"],
            lap_end=current_event["end_lap"],
            event_type=current_event["type"],
            duration_laps=max(1, current_event["end_lap"] - current_event["start_lap"]),
        ))

    return sc_events


def _timestamp_to_lap(session: fastf1.core.Session, timestamp) -> int:
    """Approximate lap number from a session timestamp."""
    try:
        laps = session.laps
        if laps is None or laps.empty:
            return 0
        # Use the first driver's laps as a reference timeline
        ref_laps = laps[laps["DriverNumber"] == laps["DriverNumber"].iloc[0]].copy()
        ref_laps = ref_laps.dropna(subset=["LapStartTime"])

        for _, lap in ref_laps.iterrows():
            lap_start = lap["LapStartTime"]
            if pd.notna(lap_start) and lap_start <= timestamp:
                return int(lap["LapNumber"])
        return 1
    except Exception:
        return 0


def _driver_pit_laps(driver: DriverSessionData) -> list[int]:
    """Get the lap numbers when this driver pitted."""
    pit_laps = []
    for stint in driver.stints[:-1]:  # all stints except last (no pit after last stint)
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

    Luck scoring:
      +30  per SC that deployed while driver was about to pit (within 3 laps)
      +50  per pit stop made UNDER SC (saved the pit loss)
      -30  per SC that deployed just after driver pitted (wasted fresh tyres)
      -20  per SC that neutralised a gap the driver had built
    """
    pit_laps = _driver_pit_laps(driver)
    luck_score = 0.0
    events_log: list[dict] = []

    for sc in sc_events:
        for pit_lap in pit_laps:

            # Case 1: Driver pitted UNDER the SC window → very lucky
            if sc.lap_start <= pit_lap <= sc.lap_end:
                luck_score += 50
                events_log.append({
                    "type": sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact": "+50 (pitted under SC — saved pit loss)",
                })

            # Case 2: SC deployed 1–3 laps AFTER driver pitted → unlucky
            elif 1 <= (sc.lap_start - pit_lap) <= 3:
                luck_score -= 30
                events_log.append({
                    "type": sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact": f"-30 (SC {sc.lap_start - pit_lap} laps after pit — unlucky)",
                })

            # Case 3: SC deployed 1–3 laps BEFORE driver due to pit → lucky
            elif 1 <= (pit_lap - sc.lap_end) <= 3:
                luck_score += 30
                events_log.append({
                    "type": sc.event_type,
                    "sc_laps": f"{sc.lap_start}–{sc.lap_end}",
                    "pit_lap": pit_lap,
                    "impact": f"+30 (SC ended {pit_lap - sc.lap_end} laps before pit — lucky)",
                })

    # Clamp to [-100, 100]
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
        # No SC periods — everyone neutral
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