# f1pitwall/scoring_engine/pace_efficiency.py
"""
Pace Efficiency score:
  - median race lap time vs teammate (normalised)
  - delta to session fastest lap (normalised)
"""
import numpy as np
from f1pitwall.models.driver import DriverSessionData
from .base import ScoreComponent, normalise_to_100

# Maps team name → list of driver codes in this session
TeamMap = dict[str, list[str]]


def _build_team_map(drivers: dict[str, DriverSessionData]) -> TeamMap:
    team_map: TeamMap = {}
    for code, d in drivers.items():
        team_map.setdefault(d.team, []).append(code)
    return team_map


def _median_lap_time(driver: DriverSessionData) -> float | None:
    times = [l.lap_time_s for l in driver.valid_laps if l.lap_time_s]
    return float(np.median(times)) if times else None


def score_pace_efficiency(
    drivers: dict[str, DriverSessionData],
) -> dict[str, ScoreComponent]:
    team_map = _build_team_map(drivers)
    medians = {code: _median_lap_time(d) for code, d in drivers.items()}

    # Session fastest valid lap
    all_medians = [v for v in medians.values() if v is not None]
    session_best = min(all_medians) if all_medians else None

    results: dict[str, ScoreComponent] = {}

    for code, driver in drivers.items():
        my_median = medians[code]
        if my_median is None or session_best is None:
            results[code] = ScoreComponent(
                name="Pace Efficiency",
                raw_value=0.0,
                score=50.0,
                notes="Insufficient data",
            )
            continue

        # --- 1. Delta to session fastest (lower is better) ---
        session_delta = my_median - session_best  # seconds behind best

        # --- 2. Teammate delta ---
        teammates = [c for c in team_map.get(driver.team, []) if c != code]
        if teammates:
            teammate_medians = [
                medians[t] for t in teammates if medians[t] is not None
            ]
            teammate_avg = float(np.mean(teammate_medians)) if teammate_medians else my_median
            teammate_delta = my_median - teammate_avg   # negative = faster
        else:
            teammate_delta = 0.0

        # Normalise both across all drivers
        all_session_deltas = [
            (medians[c] - session_best)
            for c in drivers
            if medians[c] is not None
        ]
        all_teammate_deltas = []
        for c2, d2 in drivers.items():
            m2 = medians[c2]
            if m2 is None:
                continue
            mates = [c for c in team_map.get(d2.team, []) if c != c2]
            if mates:
                mate_m = [medians[t] for t in mates if medians[t] is not None]
                if mate_m:
                    all_teammate_deltas.append(m2 - float(np.mean(mate_m)))

        session_score = normalise_to_100(
            session_delta,
            best=min(all_session_deltas),
            worst=max(all_session_deltas),
            higher_is_better=False,
        )
        teammate_score = normalise_to_100(
            teammate_delta,
            best=min(all_teammate_deltas) if all_teammate_deltas else teammate_delta,
            worst=max(all_teammate_deltas) if all_teammate_deltas else teammate_delta,
            higher_is_better=False,
        ) if all_teammate_deltas else 50.0

        blended = 0.5 * session_score + 0.5 * teammate_score

        results[code] = ScoreComponent(
            name="Pace Efficiency",
            raw_value=session_delta,
            score=round(blended, 2),
            notes=f"Session Δ: +{session_delta:.3f}s, Teammate Δ: {teammate_delta:+.3f}s",
        )

    return results