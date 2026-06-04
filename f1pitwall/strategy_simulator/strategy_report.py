# f1pitwall/strategy_simulator/strategy_report.py
"""
Strategy Report — combines pit analysis, undercut simulation,
and SC luck index into one unified output per driver.
"""
from dataclasses import dataclass, field
import fastf1.core

from f1pitwall.models.driver import DriverSessionData
from f1pitwall.models.session import SessionInfo
from .pit_analyser import PitAnalysis, analyse_all_drivers_pits
from .undercut_sim import UndercutAnalysis, analyse_undercuts
from .safety_car import DriverSCImpact, compute_sc_luck_all


@dataclass
class DriverStrategyReport:
    driver_code: str
    full_name: str
    team: str
    pit_analysis: PitAnalysis | None = None
    undercut_analysis: UndercutAnalysis | None = None
    sc_impact: DriverSCImpact | None = None

    def summary(self) -> str:
        lines = [
            f"\n{'='*55}",
            f"  {self.full_name} ({self.driver_code}) — {self.team}",
            f"{'─'*55}",
        ]

        # Pit stops
        if self.pit_analysis:
            lines.append(f"  PIT STRATEGY: {self.pit_analysis.strategy_summary}")
            for ev in self.pit_analysis.pit_events:
                verdict_color = {
                    "optimal": "✓",
                    "early":   "↑",
                    "late":    "↓",
                }.get(ev.timing_verdict, "?")
                lines.append(
                    f"    Stop {ev.stint_in}→{ev.stint_out}  "
                    f"Lap {ev.pit_lap}  "
                    f"{ev.compound_in.value}→{ev.compound_out.value}  "
                    f"window [{ev.optimal_window_start}–{ev.optimal_window_end}]  "
                    f"{verdict_color} {ev.timing_verdict.upper()}  "
                    f"loss: {ev.pit_loss_s:.1f}s"
                )

        # Undercut
        if self.undercut_analysis and self.undercut_analysis.best_scenario:
            sc = self.undercut_analysis.best_scenario
            lines.append(f"  UNDERCUT SIM:  vs {sc.rival_code} — {sc.verdict}")

        # SC luck
        if self.sc_impact:
            lines.append(f"  SC LUCK:       {self.sc_impact.summary}")

        lines.append("=" * 55)
        return "\n".join(lines)


def build_strategy_reports(
    drivers: dict[str, DriverSessionData],
    session: fastf1.core.Session,
    session_info: SessionInfo,
    total_race_laps: int | None = None,
) -> dict[str, DriverStrategyReport]:
    """
    Build full strategy reports for all drivers.

    Args:
        drivers:          parsed driver data
        session:          loaded FastF1 session
        session_info:     SessionInfo metadata
        total_race_laps:  override lap count (auto-detected if None)

    Returns:
        dict of driver_code → DriverStrategyReport
    """
    # Auto-detect total laps
    if total_race_laps is None:
        all_lap_nums = [
            l.lap_number
            for d in drivers.values()
            for l in d.laps
        ]
        total_race_laps = max(all_lap_nums) if all_lap_nums else 60

    # Run all three analyses
    pit_analyses     = analyse_all_drivers_pits(drivers, total_race_laps)
    undercut_analyses = analyse_undercuts(drivers)
    sc_impacts       = compute_sc_luck_all(drivers, session)

    reports: dict[str, DriverStrategyReport] = {}

    for code, driver in drivers.items():
        reports[code] = DriverStrategyReport(
            driver_code=code,
            full_name=driver.full_name,
            team=driver.team,
            pit_analysis=pit_analyses.get(code),
            undercut_analysis=undercut_analyses.get(code),
            sc_impact=sc_impacts.get(code),
        )

    return reports