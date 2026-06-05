# f1pitwall/driver_dna/clustering.py
"""
KMeans clustering + PCA dimensionality reduction on driver DNA vectors.
Groups drivers by driving style and produces 2D coordinates for plotting.
"""
import numpy as np
from dataclasses import dataclass, field
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from f1pitwall.driver_dna.feature_builder import DriverDNAVector, FEATURE_NAMES


@dataclass
class ClusterResult:
    driver_code: str
    full_name: str
    team: str
    cluster_id: int
    cluster_label: str        # human-readable label
    pca_x: float              # 2D PCA coordinate
    pca_y: float
    features: dict[str, float]


@dataclass
class ClusteringOutput:
    clusters: dict[str, ClusterResult]
    n_clusters: int
    cluster_labels: dict[int, str]       # cluster_id → label
    pca_variance_explained: list[float]  # variance explained by PC1, PC2
    feature_importance: dict[str, float] # which features drive PC1 most


# Heuristic cluster labels based on dominant feature patterns
def _label_cluster(
    cluster_id: int,
    cluster_centers: np.ndarray,
    feature_names: list[str],
) -> str:
    """
    Assign a human-readable label to a cluster based on its centroid.
    """
    center = cluster_centers[cluster_id]
    feature_map = dict(zip(feature_names, center))

    aggression    = feature_map.get("aggression", 0.5)
    pace_peak     = feature_map.get("pace_peak", 0.5)
    tyre_pres     = feature_map.get("tyre_preservation", 0.5)
    consistency   = feature_map.get("consistency", 0.5)
    late_pace     = feature_map.get("late_race_pace", 0.5)

    # Simple heuristic labelling
    if pace_peak > 0.75 and aggression > 0.6:
        return "Racer"
    elif tyre_pres > 0.7 and consistency > 0.7:
        return "Tyre Manager"
    elif aggression > 0.7 and tyre_pres < 0.4:
        return "Aggressive"
    elif consistency > 0.75 and pace_peak > 0.6:
        return "All-Rounder"
    elif late_pace > 0.7 and tyre_pres > 0.6:
        return "Strong Finisher"
    elif pace_peak < 0.4 and consistency > 0.6:
        return "Consistent Backmarker"
    else:
        return f"Style {cluster_id + 1}"


def cluster_drivers(
    dna_vectors: dict[str, DriverDNAVector],
    n_clusters: int = 4,
    random_state: int = 42,
) -> ClusteringOutput:
    """
    Run KMeans clustering and PCA on driver DNA vectors.

    Args:
        dna_vectors:  output of build_dna_vectors()
        n_clusters:   number of style clusters (default 4)
        random_state: for reproducibility

    Returns:
        ClusteringOutput with cluster assignments and 2D PCA coords
    """
    codes   = list(dna_vectors.keys())
    matrix  = np.array([dna_vectors[c].vector for c in codes])

    if len(codes) < n_clusters:
        n_clusters = len(codes)

    # Standardise for PCA + KMeans
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    # KMeans clustering
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=20,
    )
    cluster_ids = kmeans.fit_predict(matrix_scaled)

    # PCA for 2D visualisation
    pca = PCA(n_components=2, random_state=random_state)
    coords_2d = pca.fit_transform(matrix_scaled)

    # Variance explained
    variance_explained = pca.explained_variance_ratio_.tolist()

    # Feature importance for PC1 (loadings)
    feature_importance = {
        name: abs(float(pca.components_[0][i]))
        for i, name in enumerate(FEATURE_NAMES)
    }

    # Cluster labels from centroids
    # Inverse-transform cluster centers back to feature space
    centers_scaled = kmeans.cluster_centers_
    centers_original = scaler.inverse_transform(centers_scaled)

    cluster_labels: dict[int, str] = {
        i: _label_cluster(i, centers_original, FEATURE_NAMES)
        for i in range(n_clusters)
    }

    # Build results
    cluster_results: dict[str, ClusterResult] = {}
    for idx, code in enumerate(codes):
        dna = dna_vectors[code]
        cid = int(cluster_ids[idx])
        cluster_results[code] = ClusterResult(
            driver_code=code,
            full_name=dna.full_name,
            team=dna.team,
            cluster_id=cid,
            cluster_label=cluster_labels[cid],
            pca_x=float(coords_2d[idx, 0]),
            pca_y=float(coords_2d[idx, 1]),
            features=dna.features,
        )

    return ClusteringOutput(
        clusters=cluster_results,
        n_clusters=n_clusters,
        cluster_labels=cluster_labels,
        pca_variance_explained=variance_explained,
        feature_importance=feature_importance,
    )


def find_optimal_clusters(
    dna_vectors: dict[str, DriverDNAVector],
    max_k: int = 8,
) -> tuple[int, list[float]]:
    """
    Use the elbow method to find the optimal number of clusters.

    Returns:
        (optimal_k, inertia_values_per_k)
    """
    codes  = list(dna_vectors.keys())
    matrix = np.array([dna_vectors[c].vector for c in codes])
    scaler = StandardScaler()
    matrix_scaled = scaler.fit_transform(matrix)

    inertias: list[float] = []
    k_range = range(2, min(max_k + 1, len(codes)))

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(matrix_scaled)
        inertias.append(float(km.inertia_))

    # Simple elbow detection: largest drop in inertia
    if len(inertias) < 2:
        return 3, inertias

    drops = [inertias[i] - inertias[i+1] for i in range(len(inertias)-1)]
    optimal_idx = drops.index(max(drops))
    optimal_k = list(k_range)[optimal_idx + 1]

    return optimal_k, inertias