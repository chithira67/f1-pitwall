# f1pitwall/strategy_simulator/undercut_sim.py
"""
Undercut / Overcut Simulator

An undercut works when:
  driver pits early → gets fresh tyres → faster lap times →
  emerges ahead of rival who is still on older rubber

We simulate: "What would have happened if this driver pitted N laps
earlier or later?" and compute the estimated position delta.
"""
import numpy as np
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData, StintSummary
from f1pitwall.models.lap import TyreCompound

# Tyre warmup penalty — first 2 laps on fresh tyres are slower
WARMUP_LAPS = 2
WARMUP_PENALTY_S = [1.5, 0.6]  # lap 1, lap 2 after pit


@dataclass
class UndercutScenario:
    """Result of simulating an undercut attempt."""
    driver_code: str
    rival_code: str
    pit_lap_actual: int
    pit_lap_simulated: int          # N laps earlier
    gap_before_pit_s: float         # gap to rival before pit (positive = behind)
    gap_after_sim_s: float          # estimated gap after simulated strategy
    position_delta: float           # negative = gained positions (better)
    success: bool                   # did the undercut work?
    verdict: str


@dataclass
class UndercutAnalysis:
    """Full undercut analysis for a driver across all pit stops."""
    driver_code: str
    full_name: str
    scenarios: list[UndercutScenario] = field(default_factory=list)
    best_scenario: UndercutScenario | None = None


def _get_lap_time_at(driver: DriverSessionData, lap_number: int) -> float | None:
    """Get a driver's actual lap time at a given lap number."""
    for lap in driver.laps:
        if lap.lap_number == lap_number and lap.lap_time_s:
            return lap.lap_time_s
    return None


def _estimate_fresh_tyre_pace(
    stint_out: StintSummary,
    lap_offset: int = 3,
) -> float:
    """
    Estimate representative pace on fresh tyres (after warmup).
    Uses laps 3–6 of the stint as the benchmark.
    """
    laps = [l.lap_time_s for l in stint_out.laps[lap_offset:lap_offset+4] if l.lap_time_s]
    if laps:
        return float(np.mean(laps))
    # fallback: use stint average
    return stint_out.avg_lap_time_s


def _estimate_worn_tyre_pace(
    stint_in: StintSummary,
    laps_to_stay_out: int,
) -> float:
    """
    Estimate pace if driver stays out N more laps on worn tyres.
    Projects forward using the degradation slope.
    """
    if not stint_in.laps:
        return stint_in.avg_lap_time_s

    current_life = len(stint_in.laps)
    projected_times = []
    for i in range(1, laps_to_stay_out + 1):
        projected = (
            stint_in.avg_lap_time_s
            + stint_in.degradation_slope * (current_life + i - len(stint_in.laps) // 2)
        )
        projected_times.append(projected)

    return float(np.mean(projected_times)) if projected_times else stint_in.avg_lap_time_s


def simulate_undercut(
    driver: DriverSessionData,
    rival: DriverSessionData,
    pit_stop_index: int = 0,
    laps_early: int = 3,
    pit_loss_s: float = 22.0,
) -> UndercutScenario | None:
    """
    Simulate pitting `laps_early` earlier than actual to undercut a rival.

    Args:
        driver:          the driver attempting the undercut
        rival:           the driver being undercut
        pit_stop_index:  which pit stop to simulate (0 = first stop)
        laps_early:      how many laps earlier to pit
        pit_loss_s:      assumed pit lane time loss

    Returns:
        UndercutScenario or None if insufficient data
    """
    if len(driver.stints) < pit_stop_index + 2:
        return None
    if len(rival.stints) < 1:
        return None

    stint_in  = driver.stints[pit_stop_index]
    stint_out = driver.stints[pit_stop_index + 1]

    actual_pit_lap = stint_in.laps[-1].lap_number if stint_in.laps else 0
    sim_pit_lap    = actual_pit_lap - laps_early

    if sim_pit_lap < 1:
        return None

    # ── Gap to rival at simulated pit lap ─────────────────────
    # Approximate from position data
    driver_pos_at_pit = next(
        (l.position for l in driver.laps if l.lap_number == sim_pit_lap and l.position),
        None
    )
    rival_pos_at_pit = next(
        (l.position for l in rival.laps if l.lap_number == sim_pit_lap and l.position),
        None
    )

    if driver_pos_at_pit and rival_pos_at_pit:
        # Rough gap estimate: each position ≈ 2s gap in midfield
        gap_before = float((driver_pos_at_pit - rival_pos_at_pit) * 2.0)
    else:
        gap_before = 0.0

    # ── Time spent by rival while driver is in the pits ───────
    rival_laps_during_pit = laps_early + 1  # rival covers these laps while driver pits
    rival_worn_pace = _estimate_worn_tyre_pace(rival.stints[0], rival_laps_during_pit)
    rival_time_on_track = rival_worn_pace * rival_laps_during_pit

    # ── Driver's simulated pace after fresh stop ──────────────
    fresh_pace = _estimate_fresh_tyre_pace(stint_out)

    # Warmup laps cost extra time
    driver_sim_time = (
        pit_loss_s
        + WARMUP_PENALTY_S[0]
        + WARMUP_PENALTY_S[1]
        + fresh_pace * (rival_laps_during_pit - WARMUP_LAPS)
    )

    # ── Gap delta ─────────────────────────────────────────────
    # Positive gap_after = still behind; negative = ahead (undercut worked)
    gap_after = gap_before + (driver_sim_time - rival_time_on_track)
    position_delta = gap_after - gap_before

    success = gap_after < 0  # driver would emerge ahead

    if success:
        verdict = f"Undercut works — driver emerges ~{abs(gap_after):.1f}s ahead"
    elif gap_after < gap_before:
        verdict = f"Undercut closes gap from {gap_before:.1f}s to {gap_after:.1f}s but not enough"
    else:
        verdict = f"Undercut fails — gap widens to {gap_after:.1f}s"

    return UndercutScenario(
        driver_code=driver.driver_code,
        rival_code=rival.driver_code,
        pit_lap_actual=actual_pit_lap,
        pit_lap_simulated=sim_pit_lap,
        gap_before_pit_s=round(gap_before, 2),
        gap_after_sim_s=round(gap_after, 2),
        position_delta=round(position_delta, 2),
        success=success,
        verdict=verdict,
    )


def analyse_undercuts(
    drivers: dict[str, DriverSessionData],
    target_pairs: list[tuple[str, str]] | None = None,
    laps_early: int = 3,
) -> dict[str, UndercutAnalysis]:
    """
    Simulate undercut opportunities across the field.

    Args:
        drivers:       all parsed driver data
        target_pairs:  specific (driver, rival) pairs to simulate.
                       If None, simulates each driver vs their teammate.
        laps_early:    how many laps early to simulate

    Returns:
        dict of driver_code → UndercutAnalysis
    """
    # Default: simulate each driver vs teammate
    if target_pairs is None:
        team_map: dict[str, list[str]] = {}
        for code, d in drivers.items():
            team_map.setdefault(d.team, []).append(code)

        target_pairs = []
        for team_drivers in team_map.values():
            if len(team_drivers) == 2:
                a, b = team_drivers
                target_pairs.append((a, b))
                target_pairs.append((b, a))

    results: dict[str, UndercutAnalysis] = {}

    for driver_code, rival_code in target_pairs:
        if driver_code not in drivers or rival_code not in drivers:
            continue

        driver = drivers[driver_code]
        rival  = drivers[rival_code]

        if driver_code not in results:
            results[driver_code] = UndercutAnalysis(
                driver_code=driver_code,
                full_name=driver.full_name,
            )

        scenario = simulate_undercut(driver, rival, laps_early=laps_early)
        if scenario:
            results[driver_code].scenarios.append(scenario)

    # Pick best scenario per driver
    for analysis in results.values():
        if analysis.scenarios:
            analysis.best_scenario = min(
                analysis.scenarios,
                key=lambda s: s.gap_after_sim_s,
            )

    return results