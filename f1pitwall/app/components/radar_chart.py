# f1pitwall/app/components/radar_chart.py
import plotly.graph_objects as go
import streamlit as st
from f1pitwall.scoring_engine.compositor import DriverRating


PILLAR_LABELS = [
    "Race Craft",
    "Pace Efficiency",
    "Tyre Management",
    "Consistency",
    "Qualifying",
]

TEAM_COLORS = {
    "Red Bull Racing":    "#3671C6",
    "Ferrari":            "#E8002D",
    "Mercedes":           "#27F4D2",
    "McLaren":            "#FF8000",
    "Aston Martin":       "#229971",
    "Alpine":             "#FF87BC",
    "Williams":           "#64C4FF",
    "RB":                 "#6692FF",
    "Kick Sauber":        "#52E252",
    "Haas F1 Team":       "#B6BABD",
}


def _get_color(team: str) -> str:
    return TEAM_COLORS.get(team, "#888888")


def render_radar(
    ratings: dict[str, DriverRating],
    selected_code: str,
    compare_code: str | None = None,
) -> None:
    """Render a radar chart for selected driver, optionally vs another."""
    st.subheader("Performance Radar")

    def make_trace(code: str, rating: DriverRating) -> go.Scatterpolar:
        values = []
        for label in PILLAR_LABELS:
            pillar_key = label
            if label in rating.pillars:
                values.append(rating.pillars[label].score)
            else:
                values.append(0.0)
        values.append(values[0])  # close the polygon

        labels = PILLAR_LABELS + [PILLAR_LABELS[0]]
        color = _get_color(rating.team)

        return go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            fillcolor=color,
            opacity=0.25,
            line=dict(color=color, width=2),
            name=f"{rating.full_name} ({code})",
        )

    fig = go.Figure()

    if selected_code in ratings:
        fig.add_trace(make_trace(selected_code, ratings[selected_code]))

    if compare_code and compare_code in ratings and compare_code != selected_code:
        fig.add_trace(make_trace(compare_code, ratings[compare_code]))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10),
            ),
            angularaxis=dict(tickfont=dict(size=11)),
        ),
        showlegend=True,
        height=420,
        margin=dict(l=40, r=40, t=40, b=40),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
    )

    st.plotly_chart(fig, use_container_width=True)

    # Compare selector
    all_names = {code: r.full_name for code, r in ratings.items()}
    compare_options = ["None"] + [
        name for code, name in all_names.items() if code != selected_code
    ]
    selected_compare_name = st.selectbox("Compare with", compare_options)

    if selected_compare_name != "None":
        compare_code = next(
            (c for c, n in all_names.items() if n == selected_compare_name),
            None,
        )
        if compare_code:
            # Re-render with comparison
            fig2 = go.Figure()
            fig2.add_trace(make_trace(selected_code, ratings[selected_code]))
            fig2.add_trace(make_trace(compare_code, ratings[compare_code]))
            fig2.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 100]),
                ),
                showlegend=True,
                height=420,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ffffff"),
            )
            st.plotly_chart(fig2, use_container_width=True)