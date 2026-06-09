# f1pitwall/app/components/dna_view.py
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import pandas as pd
from f1pitwall.driver_dna.feature_builder import FEATURE_NAMES
from f1pitwall.driver_dna.clustering import ClusteringOutput
from f1pitwall.driver_dna import DriverDNAVector
from f1pitwall.app.components.driver_images import get_driver_image, PLACEHOLDER

CLUSTER_COLORS = [
    "#FF6B6B", "#4ECDC4", "#FFE66D",
    "#A8E6CF", "#FF8B94", "#B8B8FF",
]

TEAM_COLORS = {
    "Red Bull Racing":  "#3671C6",
    "Ferrari":          "#E8002D",
    "Mercedes":         "#27F4D2",
    "McLaren":          "#FF8000",
    "Aston Martin":     "#229971",
    "Alpine":           "#FF87BC",
    "Williams":         "#64C4FF",
    "RB":               "#6692FF",
    "Kick Sauber":      "#52E252",
    "Haas F1 Team":     "#B6BABD",
}


def render_similarity_map(
    clustering: ClusteringOutput,
    dna_vectors: dict[str, DriverDNAVector],
) -> None:
    """Render the 2D PCA driver similarity map."""
    st.subheader("Driver Similarity Map")

    var1 = clustering.pca_variance_explained[0] * 100
    var2 = clustering.pca_variance_explained[1] * 100
    st.caption(
        f"PCA — PC1 explains {var1:.1f}% variance, "
        f"PC2 explains {var2:.1f}% variance"
    )

    rows = []
    for code, result in clustering.clusters.items():
        rows.append({
            "Code":    code,
            "Driver":  result.full_name,
            "Team":    result.team,
            "Cluster": result.cluster_label,
            "PCA X":   result.pca_x,
            "PCA Y":   result.pca_y,
            "Color":   TEAM_COLORS.get(result.team, "#888888"),
        })

    df = pd.DataFrame(rows)

    fig = go.Figure()

    for cluster_label in df["Cluster"].unique():
        cdf = df[df["Cluster"] == cluster_label]
        fig.add_trace(go.Scatter(
            x=cdf["PCA X"],
            y=cdf["PCA Y"],
            mode="markers+text",
            name=cluster_label,
            text=cdf["Code"],
            textposition="top center",
            textfont=dict(size=11, color="#ffffff"),
            marker=dict(
                color=cdf["Color"].tolist(),
                size=18,
                line=dict(width=2, color="#ffffff"),
                opacity=0.9,
            ),
            hovertemplate=(
                "<b>%{text}</b><br>"
                "%{customdata[0]}<br>"
                "Team: %{customdata[1]}<br>"
                "Style: " + cluster_label +
                "<extra></extra>"
            ),
            customdata=cdf[["Driver", "Team"]].values,
        ))

    fig.update_layout(
        xaxis_title=f"PC1 ({var1:.1f}% variance)",
        yaxis_title=f"PC2 ({var2:.1f}% variance)",
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis=dict(gridcolor="#333", zeroline=False),
        yaxis=dict(gridcolor="#333", zeroline=False),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            title="Driving Style",
        ),
    )

    st.plotly_chart(fig, use_container_width=True)


def render_feature_heatmap(
    dna_vectors: dict[str, DriverDNAVector],
    clustering: ClusteringOutput,
) -> None:
    """Render the DNA feature heatmap — drivers × features."""
    st.subheader("DNA Feature Heatmap")

    sorted_codes = sorted(
        dna_vectors.keys(),
        key=lambda c: (
            clustering.clusters[c].cluster_id
            if c in clustering.clusters else 99,
            c,
        )
    )

    rows = []
    for code in sorted_codes:
        dna = dna_vectors[code]
        row = {"Driver": f"{code} — {dna.full_name}"}
        for feat in FEATURE_NAMES:
            row[feat.replace("_", " ").title()] = dna.features.get(feat, 0.0)
        rows.append(row)

    df = pd.DataFrame(rows).set_index("Driver")

    fig = px.imshow(
        df,
        color_continuous_scale="RdYlGn",
        zmin=0,
        zmax=1,
        aspect="auto",
        text_auto=".2f",
    )
    fig.update_layout(
        height=max(400, len(sorted_codes) * 24 + 100),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff", size=11),
        coloraxis_colorbar=dict(title="Score"),
        xaxis=dict(side="top"),
        margin=dict(l=160, r=20, t=80, b=20),
    )
    fig.update_traces(textfont=dict(size=9))

    st.plotly_chart(fig, use_container_width=True)


def render_driver_dna_profile(
    driver_code: str,
    dna_vectors: dict[str, DriverDNAVector],
    clustering: ClusteringOutput,
    similarity_rankings: dict,
) -> None:
    """Render a detailed DNA profile for one driver."""
    if driver_code not in dna_vectors:
        st.info("No DNA data for this driver.")
        return

    dna     = dna_vectors[driver_code]
    cluster = clustering.clusters.get(driver_code)
    similar = similarity_rankings.get(driver_code, [])

    # ── Driver card with image ────────────────────────────
    col_img, col_info = st.columns([1, 3])
    with col_img:
        try:
            st.image(get_driver_image(driver_code), width=130)
        except Exception:
            st.image(PLACEHOLDER, width=130)
    with col_info:
        st.markdown(f"### {dna.full_name}")
        st.markdown(f"**Team:** {dna.team}")
        st.markdown(
            f"**Driving Style:** {cluster.cluster_label if cluster else '—'}"
        )

    st.divider()

    # ── Radar chart ───────────────────────────────────────
    labels = [f.replace("_", " ").title() for f in FEATURE_NAMES]
    values = [dna.features.get(f, 0.0) * 100 for f in FEATURE_NAMES]
    values_closed = values + [values[0]]
    labels_closed = labels + [labels[0]]

    fig = go.Figure(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        fillcolor=TEAM_COLORS.get(dna.team, "#888"),
        opacity=0.3,
        line=dict(color=TEAM_COLORS.get(dna.team, "#888"), width=2),
        name=driver_code,
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Feature breakdown bars ────────────────────────────
    st.markdown("**Feature Breakdown**")
    for feat in FEATURE_NAMES:
        val = dna.features.get(feat, 0.0)
        label = feat.replace("_", " ").title()
        st.progress(val, text=f"{label}: {val*100:.0f}%")

    # ── Similar drivers ───────────────────────────────────
    if similar:
        st.divider()
        st.markdown("**Most Similar Drivers**")

        sim_rows = []
        for s in similar[:5]:
            sim_rows.append({
                "Driver":           s.driver_b,
                "Similarity":       f"{s.similarity:.3f}",
                "Shared Strengths": ", ".join(s.shared_strengths[:3]) or "—",
                "Key Difference":   s.key_difference.replace("_", " ").title(),
            })

        # Show images for top 3 similar drivers
        top3 = similar[:3]
        img_cols = st.columns(3)
        for i, s in enumerate(top3):
            with img_cols[i]:
                try:
                    st.image(get_driver_image(s.driver_b), width=80)
                except Exception:
                    st.image(PLACEHOLDER, width=80)
                st.caption(f"{s.driver_b} — {s.similarity:.3f}")

        st.dataframe(
            pd.DataFrame(sim_rows),
            use_container_width=True,
            hide_index=True,
        )


def render_elbow_chart(inertias: list[float]) -> None:
    """Render KMeans elbow chart."""
    st.subheader("Optimal Cluster Count (Elbow Method)")
    k_values = list(range(2, 2 + len(inertias)))
    fig = go.Figure(go.Scatter(
        x=k_values,
        y=inertias,
        mode="lines+markers",
        marker=dict(size=8),
        line=dict(width=2),
    ))
    fig.update_layout(
        xaxis_title="Number of Clusters (k)",
        yaxis_title="Inertia",
        height=300,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff"),
        xaxis=dict(gridcolor="#333", dtick=1),
        yaxis=dict(gridcolor="#333"),
    )
    st.plotly_chart(fig, use_container_width=True)