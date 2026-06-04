# scripts/test_strategy.py
"""
Phase 3 — Strategy Simulator Tests
Tests: pit analyser, undercut sim, SC luck index, full report
"""
from rich.console import Console
from rich.table import Table
import traceback

console = Console()

def section(title: str):
    console.print(f"\n[bold white on blue]  {title}  [/]")

def ok(msg: str):
    console.print(f"  [bold green]PASS[/] {msg}")

def fail(msg: str, e: Exception):
    console.print(f"  [bold red]FAIL[/] {msg}")
    console.print(f"       [dim]{e}[/]")
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 1 — Imports
# ─────────────────────────────────────────────
section("TEST 1 — Imports")
try:
    from f1pitwall.strategy_simulator import (
        build_strategy_reports, DriverStrategyReport,
        analyse_all_drivers_pits, PitAnalysis,
        analyse_undercuts, UndercutAnalysis,
        compute_sc_luck_all, DriverSCImpact,
    )
    ok("All strategy_simulator imports resolved")
except Exception as e:
    fail("Import failed", e)
    raise SystemExit(1)

# ─────────────────────────────────────────────
# SETUP — Load data
# ─────────────────────────────────────────────
section("SETUP — Loading race data")
from f1pitwall.data_pipeline import (
    load_session, get_session_info,
    parse_all_drivers, save_parsed_session, load_parsed_session,
)

SEASON, ROUND = 2024, 8

# Always load FastF1 session first — needed for SC analysis
session = load_session(SEASON, ROUND, "R", load_telemetry=True)
race_info = get_session_info(session)

# Try parsed cache — only use if it has data
race_data = load_parsed_session(SEASON, ROUND, "R")
if not race_data:
    console.print("  Parsing race from FastF1...")
    race_data = parse_all_drivers(session)
    if not race_data:
        console.print("[bold red]ERROR:[/] No drivers parsed — check FastF1 data for this round.")
        raise SystemExit(1)
    save_parsed_session(SEASON, ROUND, "R", race_data)
else:
    console.print("  Loaded from parsed cache.")

# Guard against empty lap data
all_lap_nums = [l.lap_number for d in race_data.values() for l in d.laps]
if not all_lap_nums:
    console.print("[bold red]ERROR:[/] No lap data found in parsed race data.")
    raise SystemExit(1)

total_laps = max(all_lap_nums)
ok(f"Race data ready — {len(race_data)} drivers, {total_laps} laps")

# ─────────────────────────────────────────────
# TEST 2 — Pit Analyser
# ─────────────────────────────────────────────
section("TEST 2 — Pit Stop Analyser")
pit_analyses = None
try:
    pit_analyses = analyse_all_drivers_pits(race_data, total_laps)
    assert len(pit_analyses) == len(race_data)

    for code, analysis in pit_analyses.items():
        assert analysis.driver_code == code
        assert analysis.total_pit_loss_s >= 0
        assert analysis.strategy_summary != ""
        for ev in analysis.pit_events:
            assert ev.timing_verdict in ("optimal", "early", "late")
            assert ev.pit_loss_s > 0
            assert ev.optimal_window_start <= ev.optimal_window_end

    ok(f"Pit analysis complete for {len(pit_analyses)} drivers — all verdicts valid")
except Exception as e:
    fail("Pit analyser failed", e)

# ─────────────────────────────────────────────
# TEST 3 — Pit timing distribution
# ─────────────────────────────────────────────
section("TEST 3 — Pit timing distribution")
try:
    if pit_analyses:
        verdicts = {"optimal": 0, "early": 0, "late": 0}
        total_stops = 0
        for analysis in pit_analyses.values():
            for ev in analysis.pit_events:
                verdicts[ev.timing_verdict] += 1
                total_stops += 1

        ok(
            f"Total stops: {total_stops} — "
            f"Optimal: {verdicts['optimal']}, "
            f"Early: {verdicts['early']}, "
            f"Late: {verdicts['late']}"
        )
except Exception as e:
    fail("Pit timing distribution failed", e)

# ─────────────────────────────────────────────
# TEST 4 — Undercut Simulator (teammate pairs)
# ─────────────────────────────────────────────
section("TEST 4 — Undercut Simulator (teammate pairs)")
undercut_analyses = None
try:
    undercut_analyses = analyse_undercuts(race_data, laps_early=3)
    assert len(undercut_analyses) > 0

    for code, analysis in undercut_analyses.items():
        assert analysis.driver_code == code
        for sc in analysis.scenarios:
            assert sc.driver_code == code
            assert sc.rival_code != code
            assert isinstance(sc.success, bool)
            assert sc.verdict != ""

    ok(f"Undercut analysis complete — {len(undercut_analyses)} drivers analysed")
except Exception as e:
    fail("Undercut simulator failed", e)

# ─────────────────────────────────────────────
# TEST 5 — Undercut with specific pairs
# ─────────────────────────────────────────────
section("TEST 5 — Undercut Simulator (specific pairs)")
try:
    codes = list(race_data.keys())
    if len(codes) >= 4:
        pairs = [(codes[0], codes[2]), (codes[1], codes[3])]
        specific = analyse_undercuts(race_data, target_pairs=pairs, laps_early=2)
        ok(f"Specific pair undercut sim — {len(specific)} drivers")

        for code, analysis in specific.items():
            if analysis.best_scenario:
                sc = analysis.best_scenario
                console.print(
                    f"  [dim]{code} vs {sc.rival_code}: "
                    f"gap before={sc.gap_before_pit_s:+.1f}s → "
                    f"after={sc.gap_after_sim_s:+.1f}s — {sc.verdict}[/]"
                )
except Exception as e:
    fail("Specific pair undercut failed", e)

# ─────────────────────────────────────────────
# TEST 6 — SC Luck Index
# ─────────────────────────────────────────────
section("TEST 6 — Safety Car Luck Index")
sc_impacts = None
try:
    sc_impacts = compute_sc_luck_all(race_data, session)
    assert len(sc_impacts) == len(race_data)

    for code, impact in sc_impacts.items():
        assert impact.driver_code == code
        assert -100 <= impact.luck_score <= 100
        assert impact.summary != ""

    ok(f"SC luck computed for {len(sc_impacts)} drivers — all scores in [-100, 100]")

    non_neutral = {
        c: i for c, i in sc_impacts.items()
        if abs(i.luck_score) > 5
    }
    if non_neutral:
        console.print("  [dim]Non-neutral SC impacts:[/]")
        for code, impact in sorted(non_neutral.items(), key=lambda x: -x[1].luck_score):
            console.print(f"    {code}: {impact.luck_score:+.0f} — {impact.summary}")
    else:
        console.print("  [dim]No SC in this race — all neutral (expected)[/]")
except Exception as e:
    fail("SC luck index failed", e)

# ─────────────────────────────────────────────
# TEST 7 — Full strategy report
# ─────────────────────────────────────────────
section("TEST 7 — Full Strategy Report")
reports = None
try:
    reports = build_strategy_reports(race_data, session, race_info)
    assert len(reports) == len(race_data)

    for code, report in reports.items():
        assert report.driver_code == code
        assert report.pit_analysis is not None
        assert report.sc_impact is not None
        s = report.summary()
        assert report.full_name in s
        assert "PIT" in s

    ok(f"Strategy reports built for {len(reports)} drivers")
except Exception as e:
    fail("Strategy report failed", e)

# ─────────────────────────────────────────────
# TEST 8 — Summary output for top 5 finishers
# ─────────────────────────────────────────────
section("TEST 8 — Report summaries (top 5 finishers)")
try:
    if reports:
        sorted_drivers = sorted(
            race_data.items(),
            key=lambda x: (x[1].finish_position or 99),
        )
        for code, _ in sorted_drivers[:5]:
            if code in reports:
                console.print(reports[code].summary())
except Exception as e:
    fail("Summary output failed", e)

# ─────────────────────────────────────────────
# TEST 9 — Edge case: single driver
# ─────────────────────────────────────────────
section("TEST 9 — Edge case: single driver")
try:
    first_code = list(race_data.keys())[0]
    single = {first_code: race_data[first_code]}
    single_reports = build_strategy_reports(single, session, race_info, total_race_laps=total_laps)
    assert len(single_reports) == 1
    ok(f"Single-driver report built without crash ({first_code})")
except Exception as e:
    fail("Single driver edge case failed", e)

# ─────────────────────────────────────────────
# FINAL TABLE — Strategy Overview
# ─────────────────────────────────────────────
section("STRATEGY TABLE — Full Field")
if reports and pit_analyses and sc_impacts:
    table = Table(
        title=f"Strategy Overview — {race_info.country} {SEASON}",
        show_lines=True,
    )
    table.add_column("Code",     style="bold cyan", width=5)
    table.add_column("Driver",   width=22)
    table.add_column("Stops",    justify="center", width=6)
    table.add_column("Pit Loss", justify="right",  width=9)
    table.add_column("Verdicts", width=24)
    table.add_column("SC Luck",  justify="right",  width=9)
    table.add_column("SC Note",  width=32)

    for code, driver in sorted(
        race_data.items(),
        key=lambda x: (x[1].finish_position or 99),
    ):
        pa = pit_analyses.get(code)
        sc = sc_impacts.get(code)
        if not pa:
            continue

        verdicts_str = " | ".join(
            f"L{ev.pit_lap} {ev.timing_verdict[0].upper()}"
            for ev in pa.pit_events
        ) or "—"

        luck_str = f"{sc.luck_score:+.0f}" if sc else "—"
        sc_note  = sc.summary if sc else "—"

        table.add_row(
            code,
            driver.full_name,
            str(len(pa.pit_events)),
            f"{pa.total_pit_loss_s:.1f}s",
            verdicts_str,
            luck_str,
            sc_note,
        )

    console.print(table)

console.print("\n[bold green]Phase 3 strategy simulator tests complete.[/]\n")
console.print(
    "[dim]Tip: Try a race with safety cars for non-neutral SC luck scores.\n"
    "     e.g. SEASON, ROUND = 2023, 15  (Singapore — VSC)\n"
    "          SEASON, ROUND = 2024, 8   (Monaco — SC)[/]\n"
)