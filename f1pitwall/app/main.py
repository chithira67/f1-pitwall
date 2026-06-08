# f1pitwall/app/main.py
import streamlit as st

st.set_page_config(
    page_title="F1 Pitwall",
    page_icon="🏎",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
        .stApp { background: linear-gradient(180deg, #0b1020 0%, #111827 100%); }
        .block-container {
            padding-top: 0.75rem;
            padding-bottom: 1rem;
            max-width: 1300px;
        }
        div[data-testid="stTabs"] button {
            border-radius: 0.75rem 0.75rem 0 0;
            padding: 0.35rem 0.65rem;
            font-size: 0.95rem;
        }
        div[data-testid="stMetric"] {
            background: rgba(17, 24, 39, 0.82);
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 0.9rem;
            padding: 0.45rem 0.55rem;
        }
        div[data-testid="stDataFrame"] {
            border-radius: 0.85rem;
            overflow: hidden;
        }
        .stAlert, .stSuccess, .stInfo, .stWarning, .stError {
            border-radius: 0.85rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

from f1pitwall.app.components.sidebar import render_sidebar
from f1pitwall.app.components.leaderboard import render_leaderboard
from f1pitwall.app.components.radar_chart import render_radar
from f1pitwall.app.components.lap_chart import render_lap_chart, render_gap_chart
from f1pitwall.app.components.strategy_view import render_strategy_overview, render_sc_luck_table
from f1pitwall.app.components.telemetry_view import render_telemetry
from f1pitwall.scoring_engine.qualifying_perf import score_qualifying_perf
from f1pitwall.app.components.dna_view import (
    render_similarity_map,
    render_feature_heatmap,
    render_driver_dna_profile,
    render_elbow_chart,
)
from f1pitwall.app.state import (
    get_session,
    get_session_info,
    get_session_data,
    get_ratings,
    get_strategy_reports,
    get_dna_data,
)

# ── Sidebar ───────────────────────────────────────────────
season, round_number, event_name, session_type = render_sidebar()

# ── Session type flags ────────────────────────────────────
SESSION_LABELS = {
    "R":   "Race",
    "Q":   "Qualifying",
    "FP1": "Practice 1",
    "FP2": "Practice 2",
    "FP3": "Practice 3",
    "S":   "Sprint",
    "SQ":  "Sprint Qualifying",
}
IS_RACE     = session_type == "R"
IS_SPRINT   = session_type == "S"
IS_QUALI    = session_type in ("Q", "SQ")
IS_PRACTICE = session_type in ("FP1", "FP2", "FP3")

# ── Header ────────────────────────────────────────────────
st.title(f"🏎  {event_name} {season}")
st.caption("Compact race intelligence, cleaner charts, and faster comparisons.")
st.caption(
    f"Round {round_number} · "
    f"{SESSION_LABELS.get(session_type, session_type)} · "
    f"F1 Pitwall Analytics"
)
st.divider()

# ── Load core data ────────────────────────────────────────
with st.spinner("Loading session data..."):
    session   = get_session(season, round_number, session_type)
    race_info = get_session_info(session)
    race_data = get_session_data(season, round_number, session_type)

if not race_data:
    st.error("No data available for this session. Try another round.")
    st.stop()

total_laps = max(
    (l.lap_number for d in race_data.values() for l in d.laps),
    default=0,
)
all_names = {code: race_data[code].full_name for code in race_data}

# ── Build tabs based on session type ─────────────────────
if IS_RACE or IS_SPRINT:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Ratings",
        "🏁 Strategy",
        "📈 Lap Times",
        "📡 Telemetry",
        "🧬 Driver DNA",
    ])
    tab_quali = None

elif IS_QUALI:
    tab1, tab3, tab4 = st.tabs([
        "📊 Qualifying",
        "📈 Lap Times",
        "📡 Telemetry",
    ])
    tab2 = tab5 = tab_quali = None

else:  # Practice
    tab3, tab4 = st.tabs([
        "📈 Lap Times",
        "📡 Telemetry",
    ])
    tab1 = tab2 = tab5 = tab_quali = None

# ── TAB 1: Ratings (Race/Sprint) or Qualifying results ───
if tab1 is not None:
    with tab1:
        if IS_RACE or IS_SPRINT:
            with st.spinner("Computing ratings..."):
                ratings = get_ratings(season, round_number)

            selected_code = render_leaderboard(ratings)

            if selected_code:
                st.markdown(
                    "<div style='margin-top: 0.4rem;'></div>",
                    unsafe_allow_html=True,
                )
                render_radar(ratings, selected_code)

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

        elif IS_QUALI:
            import pandas as pd
            quali_scores = score_qualifying_perf(race_data)

            rows = []
            for rank, (code, comp) in enumerate(
                sorted(quali_scores.items(), key=lambda x: -x[1].score), 1
            ):
                driver = race_data[code]
                best = min(
                    (l.lap_time_s for l in driver.laps if l.lap_time_s and l.is_valid),
                    default=None,
                )
                rows.append({
                    "Rank":     rank,
                    "Code":     code,
                    "Driver":   driver.full_name,
                    "Team":     driver.team,
                    "Best Lap": f"{best:.3f}s" if best else "—",
                    "Score":    round(comp.score, 1),
                    "Notes":    comp.notes,
                })

            st.subheader("Qualifying Results")
            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
            )

# ── TAB 2: Strategy (Race/Sprint only) ───────────────────
if tab2 is not None:
    with tab2:
        with st.spinner("Building strategy reports..."):
            reports = get_strategy_reports(season, round_number)
        render_strategy_overview(reports, race_data, total_laps)
        st.divider()
        render_sc_luck_table(reports, race_data)

# ── TAB 3: Lap Times (all sessions) ──────────────────────
with tab3:
    selected_names = st.multiselect(
        "Select drivers",
        options=list(all_names.values()),
        default=list(all_names.values())[:5],
        key="lap_chart_drivers",
    )
    selected_codes = [
        code for code, name in all_names.items()
        if name in selected_names
    ]

    render_lap_chart(race_data, selected_codes)

    if IS_RACE or IS_SPRINT:
        st.divider()
        render_gap_chart(race_data, selected_codes)

# ── TAB 4: Telemetry (all sessions) ──────────────────────
with tab4:
    telem_names = st.multiselect(
        "Select drivers for telemetry",
        options=list(all_names.values()),
        default=list(all_names.values())[:2],
        key="telem_drivers",
    )
    lap_input = st.number_input(
        "Lap number (0 = fastest)",
        min_value=0,
        max_value=int(total_laps) if total_laps else 100,
        value=0,
    )

    telem_codes = [
        code for code, name in all_names.items()
        if name in telem_names
    ]
    lap_num = int(lap_input) if lap_input > 0 else None

    render_telemetry(session, telem_codes, lap_num)

# ── TAB 5: Driver DNA (Race/Sprint only) ─────────────────
if tab5 is not None:
    with tab5:
        with st.spinner("Building DNA profiles..."):
            dna_vectors, clustering, similarity, profiles, inertias = get_dna_data(
                season, round_number
            )

        if not dna_vectors:
            st.error("Could not build DNA profiles for this session.")
        else:
            subtab1, subtab2, subtab3 = st.tabs([
                "Similarity Map",
                "Feature Heatmap",
                "Driver Profile",
            ])

            with subtab1:
                render_similarity_map(clustering, dna_vectors)
                st.divider()
                render_elbow_chart(inertias)

            with subtab2:
                render_feature_heatmap(dna_vectors, clustering)

            with subtab3:
                dna_names = {
                    code: dna_vectors[code].full_name
                    for code in dna_vectors
                }
                selected_dna_name = st.selectbox(
                    "Select driver",
                    options=list(dna_names.values()),
                    key="dna_driver_select",
                )
                selected_dna_code = next(
                    (c for c, n in dna_names.items() if n == selected_dna_name),
                    None,
                )
                if selected_dna_code:
                    render_driver_dna_profile(
                        selected_dna_code,
                        dna_vectors,
                        clustering,
                        similarity,
                    )