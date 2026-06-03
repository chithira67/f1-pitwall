# f1pitwall/scoring_engine/base.py
import numpy as np
from dataclasses import dataclass


@dataclass
class ScoreComponent:
    """A single scored dimension with its raw value and 0-100 score."""
    name: str
    raw_value: float
    score: float          # 0–100
    weight: float = 1.0
    notes: str = ""


def normalise_to_100(
    value: float,
    best: float,
    worst: float,
    higher_is_better: bool = True,
) -> float:
    """
    Linearly map value into [0, 100] given observed best and worst.

    Args:
        value:            the raw metric for this driver
        best:             best observed value across all drivers
        worst:            worst observed value across all drivers
        higher_is_better: True for overtakes (more = better),
                          False for lap time delta (smaller = better)
    """
    if best == worst:
        return 50.0  # everyone tied

    if higher_is_better:
        score = (value - worst) / (best - worst) * 100
    else:
        score = (worst - value) / (worst - best) * 100

    return float(np.clip(score, 0, 100))


def z_score_to_100(values: list[float], target: float) -> float:
    """
    Convert a target value into a 0–100 score based on z-score within a field.
    Useful for consistency metrics where relative standing matters more than
    absolute range.
    """
    if len(values) < 2:
        return 50.0

    arr = np.array(values)
    mean, std = float(arr.mean()), float(arr.std())

    if std == 0:
        return 50.0

    z = (target - mean) / std
    # Invert: lower z (less deviation) = higher score
    # Map z ∈ [-3, 3] → [0, 100]
    score = 50 - (z * 16.67)  # 3σ maps to ±50
    return float(np.clip(score, 0, 100))