# f1pitwall/app/components/sidebar.py
import streamlit as st
from f1pitwall.app.state import get_schedule

CURRENT_SEASON = 2024


def render_sidebar() -> tuple[int, int, str]:
    """
    Render the sidebar session selector.
    Returns (season, round_number, event_name)
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
        options=[2024, 2023, 2022],
        index=0,
    )

    schedule = get_schedule(season)
    event_names = schedule["EventName"].tolist()
    round_numbers = schedule["RoundNumber"].tolist()

    selected_event = st.sidebar.selectbox(
        "Race",
        options=event_names,
        index=0,
    )

    round_number = int(
        round_numbers[event_names.index(selected_event)]
    )

    st.sidebar.divider()
    st.sidebar.caption(f"Round {round_number} of {len(event_names)}")
    st.sidebar.caption("Data via FastF1")

    return season, round_number, selected_event