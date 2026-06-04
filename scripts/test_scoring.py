# scripts/test_scoring.py
"""
Phase 2 — Scoring Engine Tests
Tests: all 4 scorers, compositor, output shape, value ranges
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

# ─────────────────────────────────────────────
# TEST 1 — Scoring engine imports
# ─────────────────────────────────────────────
section("TEST 1 — Imports")
try:
    from f1pitwall.scoring_engine import compute_race_ratings, DriverRating, ScoreComponent
    ok("scoring_engine top-level imports OK")
except Exception as e:
    fail("scoring_engine import failed", e)
    raise SystemExit(1)

try:
    from f1pitwall.scoring_engine.race_craft import score_race_craft
    from f1pitwall.scoring_engine.pace_efficiency import score_pace_efficiency
    from f1pitwall.scoring_engine.tyre_management import score_tyre_management
    from f1pitwall.scoring_engine.consistency import score_consistency
    from f1pitwall.scoring_engine.qualifying_perf import score_qualifying_perf
    ok("All individual scorer imports OK")
except Exception as e:
    fail("Individual scorer import failed", e)
    raise SystemExit(1)

# ─────────────────────────────────────────────
# Load data (reuse Phase 1 pipeline)
# ─────────────────────────────────────────────
section("SETUP — Loading race + quali data")
from f1pitwall.data_pipeline import (
    load_session, get_session_info,
    parse_all_drivers, parse_driver_laps,
    save_parsed_session, load_parsed_session,
)

SEASON, ROUND = 2024, 1

# Race
race_data = load_parsed_session(SEASON, ROUND, "R")
if race_data is None:
    console.print("  Parsing race from FastF1...")
    session_race = load_session(SEASON, ROUND, "R")
    race_data = parse_all_drivers(session_race)
    save_parsed_session(SEASON, ROUND, "R", race_data)
else:
    session_race = load_session(SEASON, ROUND, "R", load_telemetry=False)

race_info = get_session_info(session_race)
ok(f"Race data ready — {len(race_data)} drivers")

# Qualifying
quali_data = load_parsed_session(SEASON, ROUND, "Q")
if quali_data is None:
    console.print("  Parsing quali from FastF1...")
    session_quali = load_session(SEASON, ROUND, "Q", load_telemetry=False)
    quali_data = parse_all_drivers(session_quali)
    save_parsed_session(SEASON, ROUND, "Q", quali_data)
else:
    session_quali = load_session(SEASON, ROUND, "Q", load_telemetry=False)

ok(f"Quali data ready — {len(quali_data)} drivers")

# ─────────────────────────────────────────────
# TEST 2 — Race Craft scorer
# ─────────────────────────────────────────────
section("TEST 2 — Race Craft scorer")
try:
    rc_scores = score_race_craft(race_data)
    assert len(rc_scores) == len(race_data), "Missing drivers in output"
    for code, comp in rc_scores.items():
        assert 0 <= comp.score <= 100, f"{code} score out of range: {comp.score}"
        assert comp.name == "Race Craft"
        assert comp.notes != ""
    ok(f"Race Craft scored {len(rc_scores)} drivers — all scores in [0,100]")

    best  = max(rc_scores.items(), key=lambda x: x[1].score)
    worst = min(rc_scores.items(), key=lambda x: x[1].score)
    console.print(f"  [dim]Best:  {best[0]} = {best[1].score:.1f}  ({best[1].notes})[/]")
    console.print(f"  [dim]Worst: {worst[0]} = {worst[1].score:.1f}  ({worst[1].notes})[/]")
except Exception as e:
    fail("Race Craft scorer failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 3 — Pace Efficiency scorer
# ─────────────────────────────────────────────
section("TEST 3 — Pace Efficiency scorer")
try:
    pe_scores = score_pace_efficiency(race_data)
    assert len(pe_scores) == len(race_data)
    for code, comp in pe_scores.items():
        assert 0 <= comp.score <= 100, f"{code} score out of range: {comp.score}"
    ok(f"Pace Efficiency scored {len(pe_scores)} drivers — all scores in [0,100]")

    best = max(pe_scores.items(), key=lambda x: x[1].score)
    console.print(f"  [dim]Best: {best[0]} = {best[1].score:.1f}  ({best[1].notes})[/]")
except Exception as e:
    fail("Pace Efficiency scorer failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 4 — Tyre Management scorer
# ─────────────────────────────────────────────
section("TEST 4 — Tyre Management scorer")
try:
    tm_scores = score_tyre_management(race_data)
    assert len(tm_scores) == len(race_data)
    for code, comp in tm_scores.items():
        assert 0 <= comp.score <= 100, f"{code} score out of range: {comp.score}"
    ok(f"Tyre Management scored {len(tm_scores)} drivers — all scores in [0,100]")

    best = max(tm_scores.items(), key=lambda x: x[1].score)
    console.print(f"  [dim]Best: {best[0]} = {best[1].score:.1f}  ({best[1].notes})[/]")
except Exception as e:
    fail("Tyre Management scorer failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 5 — Consistency scorer
# ─────────────────────────────────────────────
section("TEST 5 — Consistency scorer")
try:
    cs_scores = score_consistency(race_data)
    assert len(cs_scores) == len(race_data)
    for code, comp in cs_scores.items():
        assert 0 <= comp.score <= 100, f"{code} score out of range: {comp.score}"
    ok(f"Consistency scored {len(cs_scores)} drivers — all scores in [0,100]")

    best = max(cs_scores.items(), key=lambda x: x[1].score)
    console.print(f"  [dim]Best: {best[0]} = {best[1].score:.1f}  ({best[1].notes})[/]")
except Exception as e:
    fail("Consistency scorer failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 6 — Qualifying Performance scorer
# ─────────────────────────────────────────────
section("TEST 6 — Qualifying Performance scorer")
quali_scores = None
try:
    quali_scores = score_qualifying_perf(quali_data)
    assert len(quali_scores) == len(quali_data)
    for code, comp in quali_scores.items():
        assert 0 <= comp.score <= 100, f"{code} score out of range: {comp.score}"
    ok(f"Qualifying scored {len(quali_scores)} drivers — all scores in [0,100]")

    best  = max(quali_scores.items(), key=lambda x: x[1].score)
    worst = min(quali_scores.items(), key=lambda x: x[1].score)
    console.print(f"  [dim]Best:  {best[0]} = {best[1].score:.1f}  ({best[1].notes})[/]")
    console.print(f"  [dim]Worst: {worst[0]} = {worst[1].score:.1f}  ({worst[1].notes})[/]")
except Exception as e:
    fail("Qualifying scorer failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 7 — Compositor (race only)
# ─────────────────────────────────────────────
section("TEST 7 — Compositor (race only, no quali)")
ratings_race_only = None
try:
    ratings_race_only = compute_race_ratings(race_data, session_info=race_info)
    assert len(ratings_race_only) == len(race_data)

    scores = [r.composite_score for r in ratings_race_only.values()]
    assert all(0 <= s <= 100 for s in scores), "Composite score out of [0,100]"

    # Verify sorted best → worst
    assert scores == sorted(scores, reverse=True), "Ratings not sorted"

    # Verify all 4 pillars present
    for code, rating in ratings_race_only.items():
        assert "Race Craft"      in rating.pillars
        assert "Pace Efficiency" in rating.pillars
        assert "Tyre Management" in rating.pillars
        assert "Consistency"     in rating.pillars
        assert "Qualifying"      not in rating.pillars  # not passed in

    ok(f"Compositor produced {len(ratings_race_only)} ratings, sorted, all pillars present")
except Exception as e:
    fail("Compositor (race only) failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 8 — Compositor (race + quali)
# ─────────────────────────────────────────────
section("TEST 8 — Compositor (race + quali combined)")
ratings_full = None
try:
    if quali_scores:
        # Align quali_scores keys to race_data keys (some drivers may differ)
        aligned_quali = {
            code: quali_scores[code]
            for code in race_data
            if code in quali_scores
        }
        ratings_full = compute_race_ratings(
            race_data,
            session_info=race_info,
            quali_scores=aligned_quali,
        )
        drivers_with_quali = [
            code for code, r in ratings_full.items()
            if "Qualifying" in r.pillars
        ]
        ok(f"Combined ratings: {len(drivers_with_quali)}/{len(ratings_full)} drivers have Qualifying pillar")
    else:
        console.print("  [yellow]SKIP[/] No quali scores available")
except Exception as e:
    fail("Compositor (race + quali) failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 9 — DriverRating.summary() output
# ─────────────────────────────────────────────
section("TEST 9 — DriverRating.summary() output")
try:
    if ratings_race_only:
        top_driver = list(ratings_race_only.values())[0]
        summary = top_driver.summary()
        assert top_driver.driver_code in summary
        assert "COMPOSITE" in summary
        assert "Race Craft" in summary
        ok(f"summary() output valid for {top_driver.driver_code}")
        console.print(top_driver.summary())
except Exception as e:
    fail("summary() output failed", e)

# ─────────────────────────────────────────────
# TEST 10 — Edge case: single driver session
# ─────────────────────────────────────────────
section("TEST 10 — Edge case: single driver")
try:
    single = {"VER": race_data["VER"]}
    single_ratings = compute_race_ratings(single)
    assert len(single_ratings) == 1
    assert 0 <= list(single_ratings.values())[0].composite_score <= 100
    ok("Single-driver session handled without crash")
except Exception as e:
    fail("Single driver edge case failed", e)

# ─────────────────────────────────────────────
# FINAL LEADERBOARD
# ─────────────────────────────────────────────
section("FINAL LEADERBOARD — Race + Qualifying")
ratings_to_show = ratings_full or ratings_race_only
if ratings_to_show:
    table = Table(title="2024 Bahrain GP — Driver Ratings", show_lines=True)
    table.add_column("Rank", justify="center", width=5)
    table.add_column("Code", style="bold cyan", width=5)
    table.add_column("Driver", width=22)
    table.add_column("Team", width=26)
    table.add_column("Race\nCraft", justify="right", width=8)
    table.add_column("Pace\nEff.", justify="right", width=8)
    table.add_column("Tyre\nMgmt", justify="right", width=8)
    table.add_column("Consist.", justify="right", width=8)
    table.add_column("Quali", justify="right", width=8)
    table.add_column("TOTAL", justify="right", style="bold yellow", width=7)

    for rank, (code, r) in enumerate(ratings_to_show.items(), 1):
        p = r.pillars
        table.add_row(
            str(rank),
            code,
            r.full_name,
            r.team,
            f"{p['Race Craft'].score:.1f}"      if "Race Craft"      in p else "—",
            f"{p['Pace Efficiency'].score:.1f}"  if "Pace Efficiency" in p else "—",
            f"{p['Tyre Management'].score:.1f}"  if "Tyre Management" in p else "—",
            f"{p['Consistency'].score:.1f}"      if "Consistency"     in p else "—",
            f"{p['Qualifying'].score:.1f}"       if "Qualifying"      in p else "—",
            f"{r.composite_score:.1f}",
        )
    console.print(table)

console.print("\n[bold green]Phase 2 scoring tests complete.[/]\n")