# f1pitwall/app/components/leaderboard.py
import pandas as pd
import streamlit as st
from f1pitwall.scoring_engine.compositor import DriverRating


def render_leaderboard(ratings: dict[str, DriverRating]) -> str | None:
    """
    Render the driver ratings leaderboard table.
    Returns the selected driver code.
    """
    st.subheader("Driver Ratings")

    rows = []
    for rank, (code, r) in enumerate(ratings.items(), 1):
        p = r.pillars
        rows.append({
            "Rank":       rank,
            "Driver":     r.full_name,
            "Team":       r.team,
            "Race Craft": round(p["Race Craft"].score, 1)      if "Race Craft"      in p else None,
            "Pace":       round(p["Pace Efficiency"].score, 1) if "Pace Efficiency" in p else None,
            "Tyres":      round(p["Tyre Management"].score, 1) if "Tyre Management" in p else None,
            "Consist.":   round(p["Consistency"].score, 1)     if "Consistency"     in p else None,
            "Quali":      round(p["Qualifying"].score, 1)      if "Qualifying"      in p else None,
            "TOTAL":      r.composite_score,
        })

    df = pd.DataFrame(rows)

    # Colour the TOTAL column as a heatmap
    styled = df.style.background_gradient(
        subset=["TOTAL"],
        cmap="RdYlGn",
        vmin=0,
        vmax=100,
    ).background_gradient(
        subset=["Race Craft", "Pace", "Tyres", "Consist."],
        cmap="RdYlGn",
        vmin=0,
        vmax=100,
    ).format(precision=1)

    st.dataframe(styled, width="stretch", hide_index=True)

    # Driver selector for detail view
    driver_names = [r.full_name for r in ratings.values()]
    selected_name = st.selectbox("Select driver for detail view", driver_names)

    selected_code = next(
        (code for code, r in ratings.items() if r.full_name == selected_name),
        None,
    )
    return selected_code