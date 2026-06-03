# f1pitwall/scoring_engine/compositor.py
from dataclasses import dataclass, field
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.models.session import SessionInfo
from .base import ScoreComponent
from .race_craft import score_race_craft
from .pace_efficiency import score_pace_efficiency
from .tyre_management import score_tyre_management
from .consistency import score_consistency

# Weights for each pillar — must sum to 1.0
PILLAR_WEIGHTS = {
    "Race Craft":           0.20,
    "Pace Efficiency":      0.30,
    "Tyre Management":      0.20,
    "Consistency":          0.15,
    "Qualifying":           0.15,   # only used when quali scores are passed in
}

RACE_WEIGHTS = {
    "Race Craft":       0.25,
    "Pace Efficiency":  0.35,
    "Tyre Management":  0.25,
    "Consistency":      0.15,
}


@dataclass
class DriverRating:
    driver_code: str
    full_name: str
    team: str
    session_key: str
    composite_score: float
    pillars: dict[str, ScoreComponent] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"\n{'='*50}",
            f"  {self.full_name} ({self.driver_code}) — {self.team}",
            f"  Session: {self.session_key}",
            f"  COMPOSITE SCORE: {self.composite_score:.1f} / 100",
            f"{'─'*50}",
        ]
        for name, comp in self.pillars.items():
            bar = "█" * int(comp.score / 5)
            lines.append(f"  {name:<22} {comp.score:>5.1f}  {bar}")
            lines.append(f"    ↳ {comp.notes}")
        lines.append("=" * 50)
        return "\n".join(lines)


def compute_race_ratings(
    drivers: dict[str, DriverSessionData],
    session_info: SessionInfo | None = None,
    quali_scores: dict[str, ScoreComponent] | None = None,
) -> dict[str, DriverRating]:
    """
    Compute composite driver ratings for a race session.

    Args:
        drivers:       output of parse_all_drivers()
        session_info:  optional SessionInfo for labelling
        quali_scores:  optional qualifying scores to include

    Returns:
        dict of driver_code → DriverRating, sorted best → worst
    """
    race_craft   = score_race_craft(drivers)
    pace_eff     = score_pace_efficiency(drivers)
    tyre_mgmt    = score_tyre_management(drivers)
    consistency  = score_consistency(drivers)

    ratings: dict[str, DriverRating] = {}
    session_key = session_info.session_key if session_info else "unknown"

    for code, driver in drivers.items():
        pillars: dict[str, ScoreComponent] = {
            "Race Craft":      race_craft[code],
            "Pace Efficiency": pace_eff[code],
            "Tyre Management": tyre_mgmt[code],
            "Consistency":     consistency[code],
        }

        weights = dict(RACE_WEIGHTS)

        if quali_scores and code in quali_scores:
            pillars["Qualifying"] = quali_scores[code]
            # Re-weight to include qualifying
            weights = {
                "Race Craft":      0.20,
                "Pace Efficiency": 0.30,
                "Tyre Management": 0.20,
                "Consistency":     0.15,
                "Qualifying":      0.15,
            }

        composite = sum(
            pillars[name].score * weights[name]
            for name in weights
            if name in pillars
        )

        ratings[code] = DriverRating(
            driver_code=code,
            full_name=driver.full_name,
            team=driver.team,
            session_key=session_key,
            composite_score=round(composite, 2),
            pillars=pillars,
        )

    return dict(sorted(ratings.items(), key=lambda x: x[1].composite_score, reverse=True))