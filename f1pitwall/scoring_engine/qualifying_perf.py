# f1pitwall/scoring_engine/qualifying_perf.py
"""
Qualifying Performance score.
Works on a Qualifying session (not race).
Measures each driver's best lap delta vs their teammate.
"""
import numpy as np
import fastf1.core
from f1pitwall.models.driver import DriverSessionData
from .base import ScoreComponent, normalise_to_100


def _best_lap(driver: DriverSessionData) -> float | None:
    times = [l.lap_time_s for l in driver.laps if l.lap_time_s and l.is_valid]
    return min(times) if times else None


def score_qualifying_perf(
    drivers: dict[str, DriverSessionData],
) -> dict[str, ScoreComponent]:
    """
    Score all drivers on qualifying performance.
    Can be called on a parsed quali session.
    """
    best_laps = {code: _best_lap(d) for code, d in drivers.items()}

    # Build team map
    team_map: dict[str, list[str]] = {}
    for code, d in drivers.items():
        team_map.setdefault(d.team, []).append(code)

    # Session pole time
    valid_times = [t for t in best_laps.values() if t is not None]
    pole_time = min(valid_times) if valid_times else None

    # Teammate deltas
    teammate_deltas: dict[str, float] = {}
    for code, driver in drivers.items():
        my_best = best_laps[code]
        if my_best is None:
            teammate_deltas[code] = 0.0
            continue
        mates = [c for c in team_map.get(driver.team, []) if c != code]
        mate_bests = [best_laps[m] for m in mates if best_laps.get(m)]
        if mate_bests:
            teammate_deltas[code] = my_best - float(np.mean(mate_bests))
        else:
            teammate_deltas[code] = 0.0

    all_deltas = list(teammate_deltas.values())

    results: dict[str, ScoreComponent] = {}
    for code in drivers:
        my_best = best_laps[code]
        pole_delta = (my_best - pole_time) if (my_best and pole_time) else 0.0

        # Score vs pole
        all_pole_deltas = [
            (best_laps[c] - pole_time)
            for c in drivers
            if best_laps[c] and pole_time
        ]
        pole_score = normalise_to_100(
            pole_delta,
            best=min(all_pole_deltas),
            worst=max(all_pole_deltas),
            higher_is_better=False,
        ) if all_pole_deltas else 50.0

        # Score vs teammate
        tm_score = normalise_to_100(
            teammate_deltas[code],
            best=min(all_deltas),
            worst=max(all_deltas),
            higher_is_better=False,
        )

        blended = 0.5 * pole_score + 0.5 * tm_score

        results[code] = ScoreComponent(
            name="Qualifying Performance",
            raw_value=pole_delta,
            score=round(blended, 2),
            notes=f"Δ to pole: +{pole_delta:.3f}s, Teammate Δ: {teammate_deltas[code]:+.3f}s",
        )

    return results