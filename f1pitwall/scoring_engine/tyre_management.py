# f1pitwall/scoring_engine/tyre_management.py
"""
Tyre Management score:
  - degradation slope per stint (seconds lost per lap — lower is better)
  - late-stint pace stability (std of last 30% of a stint)
"""
import numpy as np
from f1pitwall.models.driver import DriverSessionData
from .base import ScoreComponent, normalise_to_100


def _avg_degradation_slope(driver: DriverSessionData) -> float:
    """Mean degradation slope across all stints with 3+ laps."""
    slopes = [
        s.degradation_slope
        for s in driver.stints
        if len(s.laps) >= 3
    ]
    return float(np.mean(slopes)) if slopes else 0.0


def _late_stint_stability(driver: DriverSessionData) -> float:
    """
    Std dev of lap times in the last 30% of each stint.
    Lower = more stable under tyre wear.
    """
    stdevs: list[float] = []
    for stint in driver.stints:
        laps = [l for l in stint.laps if l.lap_time_s]
        if len(laps) < 4:
            continue
        cutoff = max(1, int(len(laps) * 0.7))
        late_times = [l.lap_time_s for l in laps[cutoff:]]  # type: ignore
        if len(late_times) >= 2:
            stdevs.append(float(np.std(late_times)))
    return float(np.mean(stdevs)) if stdevs else 0.0


def score_tyre_management(
    drivers: dict[str, DriverSessionData],
) -> dict[str, ScoreComponent]:
    deg_slopes = {code: _avg_degradation_slope(d) for code, d in drivers.items()}
    stability = {code: _late_stint_stability(d) for code, d in drivers.items()}

    slope_vals = list(deg_slopes.values())
    stab_vals = list(stability.values())

    results: dict[str, ScoreComponent] = {}

    for code in drivers:
        deg_score = normalise_to_100(
            deg_slopes[code],
            best=min(slope_vals),
            worst=max(slope_vals),
            higher_is_better=False,  # lower slope = better tyre management
        )
        stab_score = normalise_to_100(
            stability[code],
            best=min(stab_vals),
            worst=max(stab_vals),
            higher_is_better=False,  # lower std = more stable
        )
        blended = 0.6 * deg_score + 0.4 * stab_score

        results[code] = ScoreComponent(
            name="Tyre Management",
            raw_value=deg_slopes[code],
            score=round(blended, 2),
            notes=f"Avg deg slope: {deg_slopes[code]:+.4f}s/lap, Late-stint σ: {stability[code]:.4f}s",
        )

    return results