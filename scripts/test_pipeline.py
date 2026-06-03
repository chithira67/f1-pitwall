# scripts/test_pipeline.py
"""
Phase 1 — Data Pipeline Tests
Tests: session loading, caching, parsing, domain models
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
# TEST 1 — Imports
# ─────────────────────────────────────────────
section("TEST 1 — Imports")
try:
    from f1pitwall.data_pipeline import (
        load_session, get_session_info, list_rounds,
        parse_driver_laps, parse_all_drivers,
        save_parsed_session, load_parsed_session,
    )
    ok("All data_pipeline imports resolved")
except Exception as e:
    fail("Import failed", e)
    raise SystemExit(1)

try:
    from f1pitwall.models.session import SessionInfo, SessionType
    from f1pitwall.models.lap import LapData, TyreCompound
    from f1pitwall.models.driver import DriverSessionData, StintSummary
    ok("All model imports resolved")
except Exception as e:
    fail("Model import failed", e)
    raise SystemExit(1)

try:
    from f1pitwall.config import CACHE_DIR, DEFAULT_SEASON
    ok(f"Config loaded — cache dir: {CACHE_DIR}")
except Exception as e:
    fail("Config import failed", e)
    raise SystemExit(1)

# ─────────────────────────────────────────────
# TEST 2 — Season schedule
# ─────────────────────────────────────────────
section("TEST 2 — Season schedule")
try:
    schedule = list_rounds(2024)
    assert len(schedule) > 0, "Schedule is empty"
    assert "RoundNumber" in schedule.columns
    assert "EventName" in schedule.columns
    ok(f"2024 schedule loaded — {len(schedule)} rounds")
    console.print(f"  [dim]First event: {schedule.iloc[0]['EventName']}[/]")
except Exception as e:
    fail("Schedule load failed", e)

# ─────────────────────────────────────────────
# TEST 3 — Session loading (Race)
# ─────────────────────────────────────────────
section("TEST 3 — Session loading (Race)")
SEASON, ROUND, SESSION = 2024, 1, "R"
session_race = None
try:
    session_race = load_session(SEASON, ROUND, SESSION, load_telemetry=True)
    assert session_race is not None
    ok(f"Race session loaded: {session_race.event['EventName']}")
except Exception as e:
    fail("Race session load failed", e)

# ─────────────────────────────────────────────
# TEST 4 — Session loading (Qualifying)
# ─────────────────────────────────────────────
section("TEST 4 — Session loading (Qualifying)")
session_quali = None
try:
    session_quali = load_session(SEASON, ROUND, "Q", load_telemetry=False)
    assert session_quali is not None
    ok(f"Quali session loaded: {session_quali.event['EventName']}")
except Exception as e:
    fail("Quali session load failed", e)

# ─────────────────────────────────────────────
# TEST 5 — get_session_info (Race + Quali)
# ─────────────────────────────────────────────
section("TEST 5 — get_session_info")
info_race = None
try:
    if session_race:
        info_race = get_session_info(session_race)
        assert info_race.session_type == SessionType.RACE
        assert info_race.season == 2024
        assert info_race.round_number == 1
        assert info_race.country != ""
        ok(f"Race info: {info_race.country}, {info_race.circuit}, key={info_race.session_key}")
    else:
        console.print("  [yellow]SKIP[/] No race session loaded")
except Exception as e:
    fail("get_session_info (race) failed", e)

try:
    if session_quali:
        info_quali = get_session_info(session_quali)
        assert info_quali.session_type == SessionType.QUALIFYING
        assert info_quali.total_laps is None   # quali has no total_laps
        ok(f"Quali info: total_laps=None (correct for quali)")
    else:
        console.print("  [yellow]SKIP[/] No quali session loaded")
except Exception as e:
    fail("get_session_info (quali) failed", e)

# ─────────────────────────────────────────────
# TEST 6 — Parse single driver
# ─────────────────────────────────────────────
section("TEST 6 — Parse single driver (VER)")
ver_data = None
try:
    if session_race:
        ver_data = parse_driver_laps(session_race, "VER")
        assert ver_data.driver_code == "VER"
        assert ver_data.full_name != ""
        assert ver_data.team != ""
        assert len(ver_data.laps) > 0
        assert len(ver_data.valid_laps) > 0
        assert ver_data.fastest_lap_s is not None
        assert ver_data.fastest_lap_s > 0
        ok(f"{ver_data.full_name} — {len(ver_data.laps)} laps, "
           f"{len(ver_data.valid_laps)} valid, "
           f"fastest: {ver_data.fastest_lap_s:.3f}s")
    else:
        console.print("  [yellow]SKIP[/] No race session loaded")
except Exception as e:
    fail("Single driver parse failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 7 — Stint summaries
# ─────────────────────────────────────────────
section("TEST 7 — Stint summaries")
try:
    if ver_data:
        assert len(ver_data.stints) > 0, "No stints computed"
        for stint in ver_data.stints:
            assert stint.avg_lap_time_s > 0
            assert isinstance(stint.degradation_slope, float)
            assert stint.compound is not None
        ok(f"VER has {len(ver_data.stints)} stints")
        for s in ver_data.stints:
            console.print(
                f"  [dim]Stint {s.stint_number}: {s.compound.value}, "
                f"{len(s.laps)} laps, avg {s.avg_lap_time_s:.3f}s, "
                f"deg slope {s.degradation_slope:+.4f}s/lap[/]"
            )
    else:
        console.print("  [yellow]SKIP[/] No VER data")
except Exception as e:
    fail("Stint summaries failed", e)

# ─────────────────────────────────────────────
# TEST 8 — Parse all drivers
# ─────────────────────────────────────────────
section("TEST 8 — Parse all drivers")
all_drivers = None
try:
    if session_race:
        all_drivers = parse_all_drivers(session_race)
        assert len(all_drivers) >= 18, f"Expected 18-20 drivers, got {len(all_drivers)}"
        for code, d in all_drivers.items():
            assert d.driver_code == code
            assert len(d.laps) > 0
        ok(f"Parsed {len(all_drivers)} drivers successfully")
    else:
        console.print("  [yellow]SKIP[/] No race session loaded")
except Exception as e:
    fail("All drivers parse failed", e)
    traceback.print_exc()

# ─────────────────────────────────────────────
# TEST 9 — Save parsed session to cache
# ─────────────────────────────────────────────
section("TEST 9 — Save parsed cache")
try:
    if all_drivers:
        path = save_parsed_session(SEASON, ROUND, SESSION, all_drivers)
        assert path.exists(), "Cache file not created"
        ok(f"Saved to {path.name} ({path.stat().st_size // 1024} KB)")
    else:
        console.print("  [yellow]SKIP[/] No driver data to save")
except Exception as e:
    fail("Save parsed session failed", e)

# ─────────────────────────────────────────────
# TEST 10 — Load parsed session from cache
# ─────────────────────────────────────────────
section("TEST 10 — Load parsed cache")
try:
    loaded = load_parsed_session(SEASON, ROUND, SESSION)
    assert loaded is not None, "Cache returned None"
    assert len(loaded) >= 18
    assert "VER" in loaded
    assert loaded["VER"].driver_code == "VER"
    assert len(loaded["VER"].laps) > 0
    ok(f"Loaded {len(loaded)} drivers from cache — VER has {len(loaded['VER'].laps)} laps")
except Exception as e:
    fail("Load parsed session failed", e)

# ─────────────────────────────────────────────
# TEST 11 — Domain model validation
# ─────────────────────────────────────────────
section("TEST 11 — Domain model field checks")
try:
    if all_drivers:
        for code, driver in list(all_drivers.items())[:5]:
            for lap in driver.valid_laps[:3]:
                assert lap.lap_time_s > 60,   f"{code} lap time suspiciously low: {lap.lap_time_s}"
                assert lap.lap_time_s < 300,  f"{code} lap time suspiciously high: {lap.lap_time_s}"
                assert lap.lap_number > 0
                assert lap.stint_number > 0
                assert lap.tyre_life >= 0
        ok("Lap field sanity checks passed (time range, lap/stint numbers)")
    else:
        console.print("  [yellow]SKIP[/] No driver data")
except Exception as e:
    fail("Domain model validation failed", e)

# ─────────────────────────────────────────────
# SUMMARY TABLE
# ─────────────────────────────────────────────
section("PIPELINE SUMMARY")
if all_drivers:
    table = Table(title="All Drivers — Phase 1 Parse", show_lines=True)
    table.add_column("Code", style="bold cyan", width=6)
    table.add_column("Driver", width=22)
    table.add_column("Team", width=28)
    table.add_column("Laps", justify="right")
    table.add_column("Valid", justify="right")
    table.add_column("Stints", justify="right")
    table.add_column("Fastest (s)", justify="right")

    for code, d in sorted(all_drivers.items()):
        table.add_row(
            code,
            d.full_name,
            d.team,
            str(len(d.laps)),
            str(len(d.valid_laps)),
            str(len(d.stints)),
            f"{d.fastest_lap_s:.3f}" if d.fastest_lap_s else "N/A",
        )
    console.print(table)

console.print("\n[bold green]Phase 1 pipeline tests complete.[/]\n")