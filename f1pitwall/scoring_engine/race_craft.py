# f1pitwall/scoring_engine/race_craft.py
"""
Race Craft score — measures on-track racecraft:
  - positions gained from grid to finish
  - overtakes attempted (proxy: position changes lap-to-lap)
"""
import numpy as np
from f1pitwall.models.driver import DriverSessionData
from .base import ScoreComponent, normalise_to_100


def compute_positions_gained(driver: DriverSessionData) -> float:
    """Grid → finish delta. Positive = gained positions."""
    if driver.grid_position is None or driver.finish_position is None:
        return 0.0
    # Grid pos 0 means started from pit lane — treat as last
    grid = driver.grid_position if driver.grid_position > 0 else 20
    return float(grid - driver.finish_position)


def compute_overtake_index(driver: DriverSessionData) -> float:
    """
    Count lap-to-lap position improvements as a proxy for overtakes.
    FastF1 doesn't give discrete overtake events, so we count
    laps where position improved vs the previous lap.
    """
    positions = [
        l.position for l in driver.valid_laps
        if l.position is not None
    ]
    if len(positions) < 2:
        return 0.0

    overtakes = sum(
        1 for a, b in zip(positions[:-1], positions[1:])
        if b < a  # lower position number = further forward
    )
    return float(overtakes)


def score_race_craft(
    drivers: dict[str, DriverSessionData],
) -> dict[str, ScoreComponent]:
    """
    Score all drivers in a session on Race Craft.

    Returns:
        dict of driver_code → ScoreComponent
    """
    # Compute raw metrics for all drivers
    pos_gained = {code: compute_positions_gained(d) for code, d in drivers.items()}
    overtake_idx = {code: compute_overtake_index(d) for code, d in drivers.items()}

    pg_values = list(pos_gained.values())
    ov_values = list(overtake_idx.values())

    results: dict[str, ScoreComponent] = {}

    for code in drivers:
        pg_score = normalise_to_100(
            pos_gained[code],
            best=max(pg_values),
            worst=min(pg_values),
            higher_is_better=True,
        )
        ov_score = normalise_to_100(
            overtake_idx[code],
            best=max(ov_values),
            worst=min(ov_values),
            higher_is_better=True,
        )
        # Weighted blend: positions gained matters more
        blended = 0.6 * pg_score + 0.4 * ov_score

        results[code] = ScoreComponent(
            name="Race Craft",
            raw_value=pos_gained[code],
            score=round(blended, 2),
            weight=1.0,
            notes=f"P gained: {pos_gained[code]:+.0f}, overtake idx: {overtake_idx[code]:.0f}",
        )

    return results