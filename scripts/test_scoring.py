# scripts/test_scoring.py
from f1pitwall.data_pipeline import (
    load_session,
    get_session_info,
    parse_all_drivers,
    save_parsed_session,
    load_parsed_session,
)
from f1pitwall.scoring_engine import compute_race_ratings

SEASON = 2023
ROUND  =  15   # Bahrain
SESSION = "Q"

# ── Load & parse ──────────────────────────────────────────
data = load_parsed_session(SEASON, ROUND, SESSION)
if data is None:
    print("Parsing from FastF1...")
    session = load_session(SEASON, ROUND, SESSION)
    info    = get_session_info(session)
    data    = parse_all_drivers(session)
    save_parsed_session(SEASON, ROUND, SESSION, data)
else:
    print("Loaded from cache.")
    session = load_session(SEASON, ROUND, SESSION, load_telemetry=False)
    info    = get_session_info(session)

# ── Score ─────────────────────────────────────────────────
ratings = compute_race_ratings(data, session_info=info)

# ── Print results ─────────────────────────────────────────
print(f"\n{'RANK':<5} {'CODE':<5} {'DRIVER':<25} {'TEAM':<30} {'SCORE':>6}")
print("─" * 75)
for rank, (code, rating) in enumerate(ratings.items(), 1):
    print(f"{rank:<5} {code:<5} {rating.full_name:<25} {rating.team:<30} {rating.composite_score:>6.1f}")

# Detailed breakdown for top 3
print("\n── Detailed breakdowns ──")
for code, rating in list(ratings.items())[:3]:
    print(rating.summary())