# f1pitwall/app/components/telemetry_view.py
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import fastf1
from f1pitwall.models.driver import DriverSessionData


def render_telemetry(
    session,
    selected_codes: list[str],
    lap_number: int | None = None,
) -> None:
    """
    Render speed, throttle, and brake traces for selected drivers
    on a specific lap (defaults to fastest lap).
    """
    st.subheader("Telemetry Traces")

    if not selected_codes:
        st.info("Select at least one driver.")
        return

    fig = make_subplots(
        rows=3, cols=1,
        shared_xaxes=True,
        subplot_titles=("Speed (km/h)", "Throttle (%)", "Brake"),
        vertical_spacing=0.08,
    )

    for code in selected_codes:
        try:
            driver_laps = session.laps.pick_drivers(code)
            if driver_laps.empty:
                continue

            if lap_number:
                lap = driver_laps[driver_laps["LapNumber"] == lap_number]
                if lap.empty:
                    lap = driver_laps.pick_fastest()
                else:
                    lap = lap.iloc[0:1]
            else:
                lap = driver_laps.pick_fastest()

            tel = lap.get_telemetry()
            if tel is None or tel.empty:
                continue

            distance = tel["Distance"].tolist()
            speed    = tel["Speed"].tolist()
            throttle = tel["Throttle"].tolist()
            brake    = tel["Brake"].astype(int).tolist()

            fig.add_trace(
                go.Scatter(
                    x=distance, y=speed,
                    mode="lines", name=code,
                    hovertemplate=f"{code}<br>%{{x:.0f}}m — %{{y:.0f}} km/h<extra></extra>",
                ),
                row=1, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=distance, y=throttle,
                    mode="lines", name=code,
                    showlegend=False,
                    hovertemplate=f"{code}<br>%{{x:.0f}}m — %{{y:.0f}}%<extra></extra>",
                ),
                row=2, col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=distance, y=brake,
                    mode="lines", name=code,
                    showlegend=False,
                    fill="tozeroy",
                    hovertemplate=f"{code}<br>%{{x:.0f}}m<extra></extra>",
                ),
                row=3, col=1,
            )

        except Exception as e:
            st.warning(f"Could not load telemetry for {code}: {e}")

    fig.update_layout(
        height=580,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis3_title="Distance (m)",
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    for i in range(1, 4):
        fig.update_xaxes(gridcolor="#333", row=i, col=1)
        fig.update_yaxes(gridcolor="#333", row=i, col=1)

    st.plotly_chart(fig, width="stretch")