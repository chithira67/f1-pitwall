# f1pitwall/scoring_engine/consistency.py
"""
Consistency Index:
  - lap time standard deviation across all valid laps in a stint
  - penalises wide variance (errors, big outlier laps)
"""
import numpy as np
from f1pitwall.models.driver import DriverSessionData
from .base import ScoreComponent, normalise_to_100, z_score_to_100


def _consistency_sigma(driver: DriverSessionData) -> float:
    """
    Weighted std dev across stints.
    Each stint's σ is weighted by its lap count so longer stints count more.
    """
    weighted_vars: list[float] = []
    weights: list[float] = []

    for stint in driver.stints:
        times = [l.lap_time_s for l in stint.laps if l.lap_time_s]
        if len(times) < 3:
            continue
        weighted_vars.append(float(np.std(times)))
        weights.append(len(times))

    if not weighted_vars:
        return 0.0

    return float(np.average(weighted_vars, weights=weights))


def score_consistency(
    drivers: dict[str, DriverSessionData],
) -> dict[str, ScoreComponent]:
    sigmas = {code: _consistency_sigma(d) for code, d in drivers.items()}
    sigma_vals = list(sigmas.values())

    results: dict[str, ScoreComponent] = {}

    for code in drivers:
        score = normalise_to_100(
            sigmas[code],
            best=min(sigma_vals),
            worst=max(sigma_vals),
            higher_is_better=False,  # lower σ = more consistent
        )
        results[code] = ScoreComponent(
            name="Consistency",
            raw_value=sigmas[code],
            score=round(score, 2),
            notes=f"Weighted σ across stints: {sigmas[code]:.4f}s",
        )

    return results