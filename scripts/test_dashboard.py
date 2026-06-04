# scripts/test_dashboard.py
"""
Phase 4 — Dashboard smoke tests (no browser needed)
Tests all components can be imported and data flows correctly
"""
from rich.console import Console
import traceback

console = Console()

def section(title): console.print(f"\n[bold white on blue]  {title}  [/]")
def ok(msg):        console.print(f"  [bold green]PASS[/] {msg}")
def fail(msg, e):
    console.print(f"  [bold red]FAIL[/] {msg}\n       [dim]{e}[/]")
    traceback.print_exc()

section("TEST 1 — App imports")
try:
    from f1pitwall.app.components.leaderboard   import render_leaderboard
    from f1pitwall.app.components.radar_chart   import render_radar
    from f1pitwall.app.components.lap_chart     import render_lap_chart, render_gap_chart
    from f1pitwall.app.components.strategy_view import render_strategy_overview, render_sc_luck_table
    from f1pitwall.app.components.telemetry_view import render_telemetry
    ok("All dashboard component imports resolved")
except Exception as e:
    fail("Import failed", e)
    raise SystemExit(1)

section("TEST 2 — State functions import")
try:
    from f1pitwall.app.state import (
        get_race_data, get_ratings, get_strategy_reports,
        get_race_session, get_schedule,
    )
    ok("State module imports resolved")
except Exception as e:
    fail("State import failed", e)
    raise SystemExit(1)

section("TEST 3 — Data flows into components")
try:
    from f1pitwall.data_pipeline import (
        load_session, get_session_info,
        parse_all_drivers, load_parsed_session, save_parsed_session,
    )
    from f1pitwall.scoring_engine import compute_race_ratings
    from f1pitwall.strategy_simulator import build_strategy_reports

    SEASON, ROUND = 2024, 1

    session = load_session(SEASON, ROUND, "R", load_telemetry=False)
    info = get_session_info(session)

    race_data = load_parsed_session(SEASON, ROUND, "R")
    if not race_data:
        session_full = load_session(SEASON, ROUND, "R", load_telemetry=True)
        race_data = parse_all_drivers(session_full)
        save_parsed_session(SEASON, ROUND, "R", race_data)

    assert race_data, "No race data"
    ok(f"Race data loaded — {len(race_data)} drivers")

    ratings = compute_race_ratings(race_data, session_info=info)
    assert ratings, "No ratings"
    ok(f"Ratings computed — {len(ratings)} drivers")

    reports = build_strategy_reports(race_data, session, info)
    assert reports, "No reports"
    ok(f"Strategy reports built — {len(reports)} drivers")

    total_laps = max(l.lap_number for d in race_data.values() for l in d.laps)
    ok(f"Total laps: {total_laps}")

except Exception as e:
    fail("Data flow failed", e)
    traceback.print_exc()

section("TEST 4 — Leaderboard DataFrame shape")
try:
    import pandas as pd
    rows = []
    for rank, (code, r) in enumerate(ratings.items(), 1):
        p = r.pillars
        rows.append({
            "Rank":  rank,
            "Code":  code,
            "TOTAL": r.composite_score,
        })
    df = pd.DataFrame(rows)
    assert len(df) == len(ratings)
    assert df["TOTAL"].between(0, 100).all()
    ok(f"Leaderboard DataFrame: {len(df)} rows, all scores in [0,100]")
except Exception as e:
    fail("Leaderboard DataFrame failed", e)

section("TEST 5 — Radar chart data shape")
try:
    PILLARS = ["Race Craft", "Pace Efficiency", "Tyre Management", "Consistency"]
    first_code = list(ratings.keys())[0]
    rating = ratings[first_code]
    for pillar in PILLARS:
        assert pillar in rating.pillars, f"Missing pillar: {pillar}"
        assert 0 <= rating.pillars[pillar].score <= 100
    ok(f"Radar data valid for {first_code} — all 4 pillars in range")
except Exception as e:
    fail("Radar chart data failed", e)

section("TEST 6 — Strategy view data shape")
try:
    sorted_drivers = sorted(
        race_data.items(),
        key=lambda x: (x[1].finish_position or 99),
    )
    for code, driver in sorted_drivers[:5]:
        report = reports.get(code)
        assert report is not None
        assert report.pit_analysis is not None
        assert report.sc_impact is not None
    ok("Strategy reports valid for top 5 finishers")
except Exception as e:
    fail("Strategy view data failed", e)

section("TEST 7 — Lap chart data shape")
try:
    sample_codes = list(race_data.keys())[:3]
    for code in sample_codes:
        driver = race_data[code]
        valid = driver.valid_laps
        assert len(valid) > 0
        times = [l.lap_time_s for l in valid]
        assert all(t > 60 for t in times)
    ok(f"Lap chart data valid for {sample_codes}")
except Exception as e:
    fail("Lap chart data failed", e)

console.print("\n[bold green]Phase 4 dashboard tests complete.[/]")
console.print("\n[bold cyan]To launch the dashboard:[/]")
console.print("  streamlit run f1pitwall/app/main.py\n")