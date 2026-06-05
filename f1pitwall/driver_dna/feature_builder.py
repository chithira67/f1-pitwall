# f1pitwall/driver_dna/feature_builder.py
"""
Driver DNA Feature Builder

Constructs a multi-dimensional identity vector for each driver
from their session data. Each dimension captures a distinct
aspect of driving style.

Dimensions:
  1. Aggression          — overtake rate, position volatility
  2. Pace Peak           — best lap delta to session fastest
  3. Tyre Preservation   — degradation slope (inverted)
  4. Consistency         — lap time sigma (inverted)
  5. Qualifying Pace     — best quali lap delta to pole
  6. Race Start          — positions gained/lost on lap 1
  7. Wet Weather         — performance delta in wet vs dry (if available)
  8. Late Race Pace      — avg pace in last 30% of race vs first 30%
"""
import numpy as np
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.models.lap import TyreCompound


@dataclass
class DriverDNAVector:
    """
    Normalised [0,1] identity vector for one driver.
    Each dimension is independently normalised across the field.
    """
    driver_code: str
    full_name: str
    team: str

    # Raw computed features (before normalisation)
    raw: dict[str, float] = field(default_factory=dict)

    # Normalised [0,1] features
    features: dict[str, float] = field(default_factory=dict)

    # Feature array for ML (same order as FEATURE_NAMES)
    vector: list[float] = field(default_factory=list)


FEATURE_NAMES = [
    "aggression",
    "pace_peak",
    "tyre_preservation",
    "consistency",
    "quali_pace",
    "race_start",
    "late_race_pace",
    "stint_length",
]


def _compute_aggression(driver: DriverSessionData) -> float:
    """
    Overtake rate + position volatility.
    How often does the driver change position?
    """
    positions = [
        l.position for l in driver.valid_laps
        if l.position is not None
    ]
    if len(positions) < 2:
        return 0.0

    changes = sum(
        abs(b - a)
        for a, b in zip(positions[:-1], positions[1:])
    )
    return changes / len(positions)


def _compute_pace_peak(
    driver: DriverSessionData,
    session_best_s: float,
) -> float:
    """
    Best lap delta to session fastest.
    Lower = closer to the front (better peak pace).
    Returns delta in seconds (positive = slower than best).
    """
    if driver.fastest_lap_s is None:
        return 99.0
    return driver.fastest_lap_s - session_best_s


def _compute_tyre_preservation(driver: DriverSessionData) -> float:
    """
    Average degradation slope across stints (inverted — lower slope = better).
    Returns mean slope in s/lap.
    """
    slopes = [
        s.degradation_slope
        for s in driver.stints
        if len(s.laps) >= 3
    ]
    return float(np.mean(slopes)) if slopes else 0.0


def _compute_consistency(driver: DriverSessionData) -> float:
    """Weighted lap time std dev across stints."""
    weighted_vars, weights = [], []
    for stint in driver.stints:
        times = [l.lap_time_s for l in stint.laps if l.lap_time_s]
        if len(times) >= 3:
            weighted_vars.append(float(np.std(times)))
            weights.append(len(times))
    if not weighted_vars:
        return 0.0
    return float(np.average(weighted_vars, weights=weights))


def _compute_race_start(driver: DriverSessionData) -> float:
    """
    Positions gained or lost on lap 1.
    Positive = gained (aggressive start), negative = lost.
    """
    if driver.grid_position is None:
        return 0.0
    lap1 = next(
        (l for l in driver.laps if l.lap_number == 1 and l.position),
        None,
    )
    if lap1 is None:
        return 0.0
    grid = driver.grid_position if driver.grid_position > 0 else 20
    return float(grid - lap1.position)


def _compute_late_race_pace(driver: DriverSessionData) -> float:
    """
    Ratio of late-race avg pace vs early-race avg pace.
    < 1.0 means driver gets faster late (good late race pace).
    > 1.0 means driver fades.
    """
    valid = driver.valid_laps
    if len(valid) < 10:
        return 1.0

    n = len(valid)
    early = valid[:n // 3]
    late  = valid[int(n * 0.7):]

    early_avg = float(np.mean([l.lap_time_s for l in early if l.lap_time_s]))
    late_avg  = float(np.mean([l.lap_time_s for l in late  if l.lap_time_s]))

    if early_avg == 0:
        return 1.0
    return late_avg / early_avg


def _compute_stint_length_preference(driver: DriverSessionData) -> float:
    """
    Average stint length in laps.
    High = prefers long stints (tyre manager).
    Low = prefers short stints (aggressive strategy).
    """
    lengths = [len(s.laps) for s in driver.stints if s.laps]
    return float(np.mean(lengths)) if lengths else 0.0


def build_dna_vectors(
    race_data: dict[str, DriverSessionData],
    quali_data: dict[str, DriverSessionData] | None = None,
) -> dict[str, DriverDNAVector]:
    """
    Build DNA vectors for all drivers in a session.

    Args:
        race_data:   parsed race session data
        quali_data:  optional qualifying session data

    Returns:
        dict of driver_code → DriverDNAVector (not yet normalised)
    """
    # Session-level reference values
    all_fastest = [
        d.fastest_lap_s for d in race_data.values()
        if d.fastest_lap_s
    ]
    session_best = min(all_fastest) if all_fastest else 90.0

    # Quali reference
    quali_best = None
    if quali_data:
        quali_bests = [
            min(l.lap_time_s for l in d.laps if l.lap_time_s and l.is_valid)
            for d in quali_data.values()
            if any(l.lap_time_s for l in d.laps if l.is_valid)
        ]
        if quali_bests:
            quali_best = min(quali_bests)

    raw_vectors: dict[str, DriverDNAVector] = {}

    for code, driver in race_data.items():
        raw = {
            "aggression":        _compute_aggression(driver),
            "pace_peak":         _compute_pace_peak(driver, session_best),
            "tyre_preservation": _compute_tyre_preservation(driver),
            "consistency":       _compute_consistency(driver),
            "race_start":        _compute_race_start(driver),
            "late_race_pace":    _compute_late_race_pace(driver),
            "stint_length":      _compute_stint_length_preference(driver),
        }

        # Qualifying pace
        if quali_data and code in quali_data and quali_best:
            q_driver = quali_data[code]
            q_times = [
                l.lap_time_s for l in q_driver.laps
                if l.lap_time_s and l.is_valid
            ]
            q_best = min(q_times) if q_times else None
            raw["quali_pace"] = (q_best - quali_best) if q_best else 5.0
        else:
            raw["quali_pace"] = 0.0

        raw_vectors[code] = DriverDNAVector(
            driver_code=code,
            full_name=driver.full_name,
            team=driver.team,
            raw=raw,
        )

    # Normalise each feature across the field to [0, 1]
    _normalise_vectors(raw_vectors)
    return raw_vectors


def _normalise_vectors(vectors: dict[str, DriverDNAVector]) -> None:
    """
    Normalise each feature dimension to [0, 1] across all drivers.
    Mutates vectors in place.

    For features where higher = better (aggression, race_start):
        normalise ascending
    For features where lower = better (pace_peak, tyre_preservation,
        consistency, quali_pace, late_race_pace):
        invert so 1.0 = best
    """
    INVERT = {
        # True = invert (lower raw = higher normalised score)
        "aggression":        False,
        "pace_peak":         True,
        "tyre_preservation": True,
        "consistency":       True,
        "quali_pace":        True,
        "race_start":        False,
        "late_race_pace":    True,
        "stint_length":      False,
    }

    for feature in FEATURE_NAMES:
        vals = [v.raw.get(feature, 0.0) for v in vectors.values()]
        min_val, max_val = min(vals), max(vals)

        for dna in vectors.values():
            raw_val = dna.raw.get(feature, 0.0)
            if max_val == min_val:
                norm = 0.5
            elif INVERT[feature]:
                norm = (max_val - raw_val) / (max_val - min_val)
            else:
                norm = (raw_val - min_val) / (max_val - min_val)

            dna.features[feature] = round(float(np.clip(norm, 0, 1)), 4)

    # Build the feature vector array
    for dna in vectors.values():
        dna.vector = [dna.features.get(f, 0.0) for f in FEATURE_NAMES]