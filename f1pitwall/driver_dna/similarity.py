# f1pitwall/driver_dna/similarity.py
"""
Driver Similarity — computes pairwise cosine similarity
between DNA vectors.
"""
import numpy as np
from dataclasses import dataclass
from f1pitwall.driver_dna.feature_builder import DriverDNAVector


@dataclass
class SimilarityResult:
    driver_a: str
    driver_b: str
    similarity: float     # 0.0 = completely different, 1.0 = identical
    shared_strengths: list[str]   # features where both score high (>0.65)
    key_difference: str           # feature with biggest gap


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def compute_similarity_matrix(
    dna_vectors: dict[str, DriverDNAVector],
) -> dict[tuple[str, str], float]:
    """
    Compute pairwise cosine similarity for all driver pairs.

    Returns:
        dict mapping (code_a, code_b) → similarity score
    """
    codes = list(dna_vectors.keys())
    matrix: dict[tuple[str, str], float] = {}

    for i, a in enumerate(codes):
        for j, b in enumerate(codes):
            if i >= j:
                continue
            sim = cosine_similarity(
                dna_vectors[a].vector,
                dna_vectors[b].vector,
            )
            matrix[(a, b)] = round(sim, 4)

    return matrix


def find_most_similar(
    driver_code: str,
    dna_vectors: dict[str, DriverDNAVector],
    top_n: int = 5,
) -> list[SimilarityResult]:
    """
    Find the N most similar drivers to a given driver.

    Returns:
        List of SimilarityResult sorted by similarity descending
    """
    from f1pitwall.driver_dna.feature_builder import FEATURE_NAMES

    if driver_code not in dna_vectors:
        return []

    target = dna_vectors[driver_code]
    results: list[SimilarityResult] = []

    for code, dna in dna_vectors.items():
        if code == driver_code:
            continue

        sim = cosine_similarity(target.vector, dna.vector)

        # Shared strengths: features where both > 0.65
        shared = [
            f for f in FEATURE_NAMES
            if target.features.get(f, 0) > 0.65
            and dna.features.get(f, 0) > 0.65
        ]

        # Key difference: feature with largest absolute gap
        diffs = {
            f: abs(target.features.get(f, 0) - dna.features.get(f, 0))
            for f in FEATURE_NAMES
        }
        key_diff = max(diffs, key=lambda x: diffs[x])

        results.append(SimilarityResult(
            driver_a=driver_code,
            driver_b=code,
            similarity=round(sim, 4),
            shared_strengths=shared,
            key_difference=key_diff,
        ))

    return sorted(results, key=lambda x: x.similarity, reverse=True)[:top_n]


def build_similarity_ranking(
    dna_vectors: dict[str, DriverDNAVector],
) -> dict[str, list[SimilarityResult]]:
    """Build similarity rankings for every driver."""
    return {
        code: find_most_similar(code, dna_vectors)
        for code in dna_vectors
    }