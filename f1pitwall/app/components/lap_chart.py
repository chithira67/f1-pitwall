# f1pitwall/app/components/lap_chart.py
import plotly.graph_objects as go
import streamlit as st
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.models.lap import TyreCompound

COMPOUND_COLORS = {
    TyreCompound.SOFT:    "#FF3333",
    TyreCompound.MEDIUM:  "#FFD700",
    TyreCompound.HARD:    "#FFFFFF",
    TyreCompound.INTER:   "#39B54A",
    TyreCompound.WET:     "#0067FF",
    TyreCompound.UNKNOWN: "#888888",
}


def render_lap_chart(
    race_data: dict[str, DriverSessionData],
    selected_codes: list[str],
) -> None:
    """Render lap time chart for selected drivers."""
    st.subheader("Lap Time Chart")

    if not selected_codes:
        st.info("Select at least one driver.")
        return

    fig = go.Figure()

    for code in selected_codes:
        if code not in race_data:
            continue

        driver = race_data[code]
        valid = driver.valid_laps

        lap_nums  = [l.lap_number for l in valid]
        lap_times = [l.lap_time_s for l in valid]
        compounds = [l.compound for l in valid]
        hovers    = [
            f"Lap {l.lap_number}<br>"
            f"Time: {l.lap_time_s:.3f}s<br>"
            f"Tyre: {l.compound.value}<br>"
            f"Life: {l.tyre_life} laps"
            for l in valid
        ]

        # Main lap time line
        fig.add_trace(go.Scatter(
            x=lap_nums,
            y=lap_times,
            mode="lines+markers",
            name=f"{code} — {driver.full_name}",
            text=hovers,
            hoverinfo="text",
            marker=dict(
                color=[COMPOUND_COLORS.get(c, "#888") for c in compounds],
                size=6,
                line=dict(width=0),
            ),
            line=dict(width=1.5),
        ))

    fig.update_layout(
        xaxis_title="Lap",
        yaxis_title="Lap Time (s)",
        yaxis=dict(autorange="reversed"),   # faster = higher on chart
        height=420,
        hovermode="x unified",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis=dict(gridcolor="#333"),
        yaxis_gridcolor="#333",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )

    # Compound legend note
    st.plotly_chart(fig, width="stretch")
    st.caption("Marker colour = tyre compound: 🔴 Soft  🟡 Medium  ⚪ Hard  🟢 Inter  🔵 Wet")


def render_gap_chart(
    race_data: dict[str, DriverSessionData],
    selected_codes: list[str],
) -> None:
    """Render position-over-laps chart."""
    st.subheader("Position Chart")

    fig = go.Figure()

    for code in selected_codes:
        if code not in race_data:
            continue

        driver = race_data[code]
        laps_with_pos = [l for l in driver.laps if l.position is not None]

        if not laps_with_pos:
            continue

        fig.add_trace(go.Scatter(
            x=[l.lap_number for l in laps_with_pos],
            y=[l.position for l in laps_with_pos],
            mode="lines",
            name=f"{code}",
            line=dict(width=2),
            hovertemplate=f"{code}<br>Lap %{{x}}<br>P%{{y}}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title="Lap",
        yaxis_title="Position",
        yaxis=dict(autorange="reversed", dtick=1),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis=dict(gridcolor="#333"),
        yaxis_gridcolor="#333",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )

    st.plotly_chart(fig, width="stretch")