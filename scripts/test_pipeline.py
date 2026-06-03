# scripts/test_pipeline.py
from f1pitwall.data_pipeline import (
    load_session,
    parse_all_drivers,
    save_parsed_session,
    load_parsed_session,
)

SEASON = 2024
ROUND = 1   # Bahrain
SESSION = "R"

# Try loading from our parsed cache first
data = load_parsed_session(SEASON, ROUND, SESSION)

if data is None:
    print("Not in parsed cache — loading from FastF1...")
    session = load_session(SEASON, ROUND, SESSION, load_telemetry=True)
    data = parse_all_drivers(session)
    path = save_parsed_session(SEASON, ROUND, SESSION, data)
    print(f"Saved parsed data to {path}")
else:
    print("Loaded from parsed cache instantly.")

# Print a summary
for code, driver in sorted(data.items()):
    valid = len(driver.valid_laps)
    fastest = f"{driver.fastest_lap_s:.3f}s" if driver.fastest_lap_s else "N/A"
    print(f"  {code:>3}  {driver.full_name:<25}  {valid:>2} valid laps  fastest: {fastest}")