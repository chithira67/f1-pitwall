# f1pitwall/app/main.py
import streamlit as st

st.set_page_config(
    page_title="F1 Pitwall",
    page_icon="🏎",
    layout="wide",
    initial_sidebar_state="expanded",
)

from f1pitwall.app.components.sidebar import render_sidebar
from f1pitwall.app.components.leaderboard import render_leaderboard
from f1pitwall.app.components.radar_chart import render_radar
from f1pitwall.app.components.lap_chart import render_lap_chart, render_gap_chart
from f1pitwall.app.components.strategy_view import render_strategy_overview, render_sc_luck_table
from f1pitwall.app.components.telemetry_view import render_telemetry
from f1pitwall.app.state import (
    get_race_data, get_ratings, get_strategy_reports,
    get_race_session, get_schedule,
)

# ── Sidebar ───────────────────────────────────────────────
season, round_number, event_name = render_sidebar()

# ── Header ────────────────────────────────────────────────
st.title(f"🏎  {event_name} {season}")
st.caption(f"Round {round_number} · F1 Pitwall Analytics")
st.divider()

# ── Load all data ─────────────────────────────────────────
with st.spinner("Loading session data..."):
    race_data = get_race_data(season, round_number)
    ratings   = get_ratings(season, round_number)
    reports   = get_strategy_reports(season, round_number)
    session   = get_race_session(season, round_number)

if not race_data:
    st.error("No data available for this session. Try another round.")
    st.stop()

total_laps = max(
    l.lap_number for d in race_data.values() for l in d.laps
)

# ── Tabs ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Ratings",
    "🏁 Strategy",
    "📈 Lap Times",
    "📡 Telemetry",
])

# ── TAB 1: Ratings ────────────────────────────────────────
with tab1:
    col1, col2 = st.columns([3, 2])

    with col1:
        selected_code = render_leaderboard(ratings)

    with col2:
        if selected_code:
            render_radar(ratings, selected_code)

    # Pillar breakdown for selected driver
    if selected_code and selected_code in ratings:
        st.divider()
        rating = ratings[selected_code]
        st.subheader(f"Breakdown — {rating.full_name}")

        cols = st.columns(len(rating.pillars))
        for i, (name, comp) in enumerate(rating.pillars.items()):
            with cols[i]:
                st.metric(
                    label=name,
                    value=f"{comp.score:.1f}",
                    delta=comp.notes,
                    delta_color="off",
                )

# ── TAB 2: Strategy ───────────────────────────────────────
with tab2:
    render_strategy_overview(reports, race_data, total_laps)
    st.divider()
    render_sc_luck_table(reports, race_data)

# ── TAB 3: Lap Times ──────────────────────────────────────
with tab3:
    all_codes = list(race_data.keys())
    all_names = {code: race_data[code].full_name for code in all_codes}

    selected_names = st.multiselect(
        "Select drivers",
        options=list(all_names.values()),
        default=list(all_names.values())[:5],
    )
    selected_codes = [
        code for code, name in all_names.items()
        if name in selected_names
    ]

    render_lap_chart(race_data, selected_codes)
    st.divider()
    render_gap_chart(race_data, selected_codes)

# ── TAB 4: Telemetry ──────────────────────────────────────
with tab4:
    col1, col2 = st.columns([3, 1])

    with col1:
        telem_names = st.multiselect(
            "Select drivers for telemetry",
            options=list(all_names.values()),
            default=list(all_names.values())[:2],
            key="telem_drivers",
        )
    with col2:
        lap_input = st.number_input(
            "Lap number (0 = fastest)",
            min_value=0,
            max_value=int(total_laps),
            value=0,
        )

    telem_codes = [
        code for code, name in all_names.items()
        if name in telem_names
    ]
    lap_num = int(lap_input) if lap_input > 0 else None

    render_telemetry(session, telem_codes, lap_num)