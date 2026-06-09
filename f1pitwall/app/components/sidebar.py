# f1pitwall/app/components/sidebar.py
import streamlit as st
import fastf1
from f1pitwall.app.state import get_schedule

SESSION_OPTIONS = {
    "Race":              "R",
    "Qualifying":        "Q",
    "Practice 1":        "FP1",
    "Practice 2":        "FP2",
    "Practice 3":        "FP3",
    "Sprint":            "S",
    "Sprint Qualifying": "SQ",
}


def _get_available_sessions(season: int, round_number: int) -> dict[str, str]:
    """
    Return only session types that actually exist for this event.
    Sprint weekends have S + SQ but no FP2/FP3.
    Normal weekends have FP1/FP2/FP3 but no S/SQ.
    """
    try:
        event = fastf1.get_event(season, round_number)
        available = {}
        for label, code in SESSION_OPTIONS.items():
            try:
                event.get_session_name(code)
                available[label] = code
            except Exception:
                pass
        return available if available else SESSION_OPTIONS
    except Exception:
        return SESSION_OPTIONS


def render_sidebar() -> tuple[int, int, str, str]:
    """
    Render the sidebar session selector.
    Returns (season, round_number, event_name, session_type)
    """
    st.sidebar.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/33/F1.svg/500px-F1.svg.png",
        width=80,
    )
    st.sidebar.title("F1 Pitwall")
    st.sidebar.caption("Analytics Platform")
    st.sidebar.divider()

    season = st.sidebar.selectbox(
        "Season",
        options=[2025, 2024, 2023, 2022],
        index=0,
    )

    schedule = get_schedule(season)
    event_names   = schedule["EventName"].tolist()
    round_numbers = schedule["RoundNumber"].tolist()

    selected_event = st.sidebar.selectbox(
        "Event",
        options=event_names,
        index=0,
    )
    round_number = int(round_numbers[event_names.index(selected_event)])

    # Only show sessions that exist for this event
    available_sessions = _get_available_sessions(season, round_number)

    selected_session_label = st.sidebar.selectbox(
        "Session",
        options=list(available_sessions.keys()),
        index=0,
    )
    session_type = available_sessions[selected_session_label]

    st.sidebar.divider()
    st.sidebar.caption(f"Round {round_number} of {len(event_names)}")
    st.sidebar.caption(f"Session: {selected_session_label}")
    st.sidebar.caption("Data via FastF1")

    return season, round_number, selected_event, session_type