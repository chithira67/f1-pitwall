# f1pitwall/app/components/strategy_view.py
import plotly.graph_objects as go
import streamlit as st
from f1pitwall.strategy_simulator.strategy_report import DriverStrategyReport
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.models.lap import TyreCompound

COMPOUND_COLORS = {
    TyreCompound.SOFT:    "#FF3333",
    TyreCompound.MEDIUM:  "#FFD700",
    TyreCompound.HARD:    "#CCCCCC",
    TyreCompound.INTER:   "#39B54A",
    TyreCompound.WET:     "#0067FF",
    TyreCompound.UNKNOWN: "#888888",
}

VERDICT_COLORS = {
    "optimal": "#00CC66",
    "early":   "#FFD700",
    "late":    "#FF4444",
}


def render_strategy_overview(
    reports: dict[str, DriverStrategyReport],
    race_data: dict[str, DriverSessionData],
    total_laps: int,
) -> None:
    """Render tyre stint visualisation and pit stop timing for all drivers."""
    st.subheader("Strategy Overview — Tyre Stints")

    # Sort by finish position
    sorted_drivers = sorted(
        race_data.items(),
        key=lambda x: (x[1].finish_position or 99),
    )

    fig = go.Figure()

    for idx, (code, driver) in enumerate(sorted_drivers):
        report = reports.get(code)
        if not report or not report.pit_analysis:
            continue

        y_pos = idx

        for stint in driver.stints:
            if not stint.laps:
                continue
            start_lap = stint.laps[0].lap_number
            end_lap   = stint.laps[-1].lap_number
            color     = COMPOUND_COLORS.get(stint.compound, "#888")

            fig.add_trace(go.Bar(
                x=[end_lap - start_lap + 1],
                y=[f"P{driver.finish_position or '?'} {code}"],
                base=start_lap - 1,
                orientation="h",
                marker=dict(color=color, line=dict(width=0.5, color="#000")),
                name=stint.compound.value,
                hovertemplate=(
                    f"{driver.full_name}<br>"
                    f"Stint {stint.stint_number}: {stint.compound.value}<br>"
                    f"Laps {start_lap}–{end_lap} "
                    f"({end_lap - start_lap + 1} laps)<br>"
                    f"Avg: {stint.avg_lap_time_s:.3f}s<br>"
                    f"Deg: {stint.degradation_slope:+.4f}s/lap"
                    "<extra></extra>"
                ),
                showlegend=False,
            ))

        # Pit stop markers
        if report.pit_analysis:
            for ev in report.pit_analysis.pit_events:
                verdict_color = VERDICT_COLORS.get(ev.timing_verdict, "#fff")
                fig.add_trace(go.Scatter(
                    x=[ev.pit_lap],
                    y=[f"P{driver.finish_position or '?'} {code}"],
                    mode="markers",
                    marker=dict(
                        symbol="triangle-down",
                        size=10,
                        color=verdict_color,
                        line=dict(width=1, color="#000"),
                    ),
                    hovertemplate=(
                        f"Pit stop — Lap {ev.pit_lap}<br>"
                        f"{ev.compound_in.value} → {ev.compound_out.value}<br>"
                        f"Timing: {ev.timing_verdict.upper()}<br>"
                        f"Window: laps {ev.optimal_window_start}–{ev.optimal_window_end}<br>"
                        f"Est. loss: {ev.pit_loss_s:.1f}s"
                        "<extra></extra>"
                    ),
                    showlegend=False,
                ))

    fig.update_layout(
        barmode="stack",
        xaxis=dict(title="Lap", range=[0, total_laps + 1], gridcolor="#333"),
        yaxis=dict(title="Driver", autorange="reversed"),
        height=max(400, len(sorted_drivers) * 28 + 80),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        margin=dict(l=120, r=20, t=40, b=40),
    )

    st.plotly_chart(fig, width="stretch")

    # Compound legend
    cols = st.columns(6)
    for i, (compound, color) in enumerate(COMPOUND_COLORS.items()):
        if compound == TyreCompound.UNKNOWN:
            continue
        cols[i % 5].markdown(
            f'<span style="color:{color}">■</span> {compound.value}',
            unsafe_allow_html=True,
        )
    st.caption("▼ Pit stop marker colour: 🟢 Optimal  🟡 Early  🔴 Late")


def render_sc_luck_table(
    reports: dict[str, DriverStrategyReport],
    race_data: dict[str, DriverSessionData],
) -> None:
    """Render safety car luck index table."""
    st.subheader("Safety Car Luck Index")

    import pandas as pd

    rows = []
    for code, driver in sorted(
        race_data.items(),
        key=lambda x: (x[1].finish_position or 99),
    ):
        report = reports.get(code)
        if not report or not report.sc_impact:
            continue
        rows.append({
            "Driver":     driver.full_name,
            "Team":       driver.team,
            "Luck Score": report.sc_impact.luck_score,
            "Summary":    report.sc_impact.summary,
        })

    if not rows:
        st.info("No strategy data available.")
        return

    df = pd.DataFrame(rows)
    styled = df.style.background_gradient(
        subset=["Luck Score"],
        cmap="RdYlGn",
        vmin=-100,
        vmax=100,
    ).format({"Luck Score": "{:+.0f}"})

    st.dataframe(styled, width="stretch", hide_index=True)