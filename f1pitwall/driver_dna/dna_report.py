# f1pitwall/driver_dna/dna_report.py
"""
DNA Report — combines feature vector, cluster assignment,
and similarity into one human-readable profile.
"""
from dataclasses import dataclass
from f1pitwall.driver_dna.feature_builder import DriverDNAVector, FEATURE_NAMES
from f1pitwall.driver_dna.clustering import ClusterResult
from f1pitwall.driver_dna.similarity import SimilarityResult


@dataclass
class DriverDNAProfile:
    driver_code: str
    full_name: str
    team: str
    dna: DriverDNAVector
    cluster: ClusterResult
    similar_drivers: list[SimilarityResult]

    def summary(self) -> str:
        lines = [
            f"\n{'='*55}",
            f"  DNA PROFILE — {self.full_name} ({self.driver_code})",
            f"  Team: {self.team}",
            f"  Style: {self.cluster.cluster_label}",
            f"{'─'*55}",
        ]

        for feat in FEATURE_NAMES:
            val = self.dna.features.get(feat, 0.0)
            bar = "█" * int(val * 20)
            pct = f"{val*100:.0f}%"
            lines.append(f"  {feat:<22} {pct:>4}  {bar}")

        lines.append(f"{'─'*55}")
        lines.append("  Most similar drivers:")
        for s in self.similar_drivers[:3]:
            lines.append(
                f"    {s.driver_b:<5} similarity: {s.similarity:.3f}  "
                f"shared: {', '.join(s.shared_strengths[:2]) or 'none'}"
            )

        lines.append("=" * 55)
        return "\n".join(lines)


def build_dna_profiles(
    dna_vectors: dict,
    clustering_output,
    similarity_rankings: dict,
) -> dict[str, DriverDNAProfile]:
    """Combine all DNA data into profiles."""
    profiles: dict[str, DriverDNAProfile] = {}

    for code, dna in dna_vectors.items():
        cluster = clustering_output.clusters.get(code)
        similar = similarity_rankings.get(code, [])

        if cluster is None:
            continue

        profiles[code] = DriverDNAProfile(
            driver_code=code,
            full_name=dna.full_name,
            team=dna.team,
            dna=dna,
            cluster=cluster,
            similar_drivers=similar,
        )

    return profiles