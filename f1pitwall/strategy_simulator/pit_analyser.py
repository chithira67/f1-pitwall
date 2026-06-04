# f1pitwall/strategy_simulator/pit_analyser.py
"""
Pit Stop Analyser
- Detects actual pit laps from stint data
- Computes time lost in the pit lane
- Estimates optimal pit window using tyre degradation slopes
- Compares actual vs optimal pit timing
"""
import numpy as np
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData, StintSummary
from f1pitwall.models.lap import TyreCompound


# Average pit lane time loss by circuit (seconds).
# Used when we can't compute it directly from telemetry.
DEFAULT_PIT_LOSS = 22.0  # seconds — conservative average

COMPOUND_PACE_DELTA = {
    # How much faster a fresh compound is vs the previous (seconds per lap)
    # Soft > Medium > Hard
    (TyreCompound.HARD,   TyreCompound.SOFT):   1.2,
    (TyreCompound.MEDIUM, TyreCompound.SOFT):   0.7,
    (TyreCompound.HARD,   TyreCompound.MEDIUM): 0.5,
    (TyreCompound.SOFT,   TyreCompound.MEDIUM): -0.5,
    (TyreCompound.SOFT,   TyreCompound.HARD):   -1.2,
    (TyreCompound.MEDIUM, TyreCompound.HARD):   -0.5,
}


@dataclass
class PitEvent:
    """A single pit stop."""
    driver_code: str
    pit_lap: int                    # lap the driver pitted ON
    stint_in: int                   # stint number before pit
    stint_out: int                  # stint number after pit
    compound_in: TyreCompound
    compound_out: TyreCompound
    pit_loss_s: float               # estimated time lost in pit lane
    optimal_window_start: int       # earliest beneficial pit lap
    optimal_window_end: int         # latest beneficial pit lap
    laps_early: int                 # positive = pitted early, negative = late
    timing_verdict: str             # "optimal", "early", "late"


@dataclass
class PitAnalysis:
    """Full pit stop analysis for one driver."""
    driver_code: str
    full_name: str
    team: str
    pit_events: list[PitEvent] = field(default_factory=list)
    total_pit_loss_s: float = 0.0
    strategy_summary: str = ""


def _estimate_pit_loss(
    driver: DriverSessionData,
    stint_in: StintSummary,
    stint_out: StintSummary,
) -> float:
    """
    Estimate time lost in pit lane.
    Uses the gap between last lap of stint_in and first lap of stint_out
    compared to their average lap times.
    """
    if not stint_in.laps or not stint_out.laps:
        return DEFAULT_PIT_LOSS

    # Last few laps before pit (exclude outlier in-lap)
    pre_pit_laps = [l.lap_time_s for l in stint_in.laps[-3:-1] if l.lap_time_s]
    # First few laps after pit (exclude outlier out-lap)
    post_pit_laps = [l.lap_time_s for l in stint_out.laps[2:5] if l.lap_time_s]

    if not pre_pit_laps or not post_pit_laps:
        return DEFAULT_PIT_LOSS

    avg_pre  = float(np.mean(pre_pit_laps))
    avg_post = float(np.mean(post_pit_laps))

    # The in-lap is usually ~20-25s slower due to pit entry
    in_lap = stint_in.laps[-1].lap_time_s if stint_in.laps[-1].lap_time_s else avg_pre + 22
    estimated_loss = in_lap - avg_pre

    # Sanity check — pit loss should be 15–35s typically
    if 10 <= estimated_loss <= 40:
        return round(estimated_loss, 2)
    return DEFAULT_PIT_LOSS


def _optimal_pit_window(
    stint: StintSummary,
    pit_loss: float,
    remaining_laps: int,
) -> tuple[int, int]:
    """
    Compute the optimal pit window using the crossover point formula.

    Crossover lap = pit_loss / degradation_slope

    This is the lap at which staying out costs more than pitting.
    Window = [crossover - 3, crossover + 3]
    """
    slope = stint.degradation_slope
    if slope <= 0:
        # No degradation detected — very late pit or no benefit
        mid = max(1, remaining_laps - 5)
        return mid, remaining_laps

    crossover = pit_loss / slope
    start = max(1, int(crossover) - 3)
    end   = int(crossover) + 3

    return start, end


def analyse_pit_stops(
    driver: DriverSessionData,
    total_race_laps: int,
) -> PitAnalysis:
    """
    Analyse all pit stops for a driver.

    Args:
        driver:           parsed DriverSessionData
        total_race_laps:  total laps in the race

    Returns:
        PitAnalysis with all pit events and timing verdicts
    """
    analysis = PitAnalysis(
        driver_code=driver.driver_code,
        full_name=driver.full_name,
        team=driver.team,
    )

    stints = driver.stints
    if len(stints) < 2:
        analysis.strategy_summary = "Single stint — no pit stops detected"
        return analysis

    total_loss = 0.0

    for i in range(len(stints) - 1):
        stint_in  = stints[i]
        stint_out = stints[i + 1]

        # The pit lap is the last lap of stint_in
        pit_lap = stint_in.laps[-1].lap_number if stint_in.laps else 0

        pit_loss = _estimate_pit_loss(driver, stint_in, stint_out)
        total_loss += pit_loss

        # Laps remaining when driver pitted
        remaining = total_race_laps - pit_lap

        opt_start, opt_end = _optimal_pit_window(stint_in, pit_loss, remaining)

        # Tyre life at the time of pit (how long they ran stint_in)
        tyre_life_at_pit = len(stint_in.laps)

        laps_early = opt_start - tyre_life_at_pit  # positive = pitted early

        if opt_start <= tyre_life_at_pit <= opt_end:
            verdict = "optimal"
        elif tyre_life_at_pit < opt_start:
            verdict = "early"
        else:
            verdict = "late"

        pit_event = PitEvent(
            driver_code=driver.driver_code,
            pit_lap=pit_lap,
            stint_in=stint_in.stint_number,
            stint_out=stint_out.stint_number,
            compound_in=stint_in.compound,
            compound_out=stint_out.compound,
            pit_loss_s=pit_loss,
            optimal_window_start=opt_start,
            optimal_window_end=opt_end,
            laps_early=laps_early,
            timing_verdict=verdict,
        )
        analysis.pit_events.append(pit_event)

    analysis.total_pit_loss_s = round(total_loss, 2)
    stops = len(analysis.pit_events)
    verdicts = [e.timing_verdict for e in analysis.pit_events]
    analysis.strategy_summary = (
        f"{stops} stop(s): {', '.join(verdicts)} | "
        f"Total pit loss: {total_loss:.1f}s"
    )

    return analysis


def analyse_all_drivers_pits(
    drivers: dict[str, DriverSessionData],
    total_race_laps: int,
) -> dict[str, PitAnalysis]:
    """Run pit analysis for every driver."""
    return {
        code: analyse_pit_stops(driver, total_race_laps)
        for code, driver in drivers.items()
    }