# f1pitwall/app/state.py
import streamlit as st
from f1pitwall.data_pipeline import (
    load_session, get_session_info as _get_session_info,
    parse_all_drivers, save_parsed_session, load_parsed_session,
)
from f1pitwall.scoring_engine import compute_race_ratings
from f1pitwall.scoring_engine.qualifying_perf import score_qualifying_perf
from f1pitwall.strategy_simulator import build_strategy_reports
from f1pitwall.models.session import SessionInfo
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.scoring_engine.compositor import DriverRating
from f1pitwall.strategy_simulator.strategy_report import DriverStrategyReport


# ── Generic session loaders ───────────────────────────────

@st.cache_resource(show_spinner="Loading session...")
def get_session(season: int, round_number: int, session_type: str = "R"):
    return load_session(season, round_number, session_type, load_telemetry=True)


def get_session_info(session) -> SessionInfo:
    return _get_session_info(session)


@st.cache_data(show_spinner="Parsing session data...")
def get_session_data(
    season: int,
    round_number: int,
    session_type: str = "R",
) -> dict[str, DriverSessionData]:
    data = load_parsed_session(season, round_number, session_type)
    if not data:
        session = get_session(season, round_number, session_type)
        data = parse_all_drivers(session)
        if data:
            save_parsed_session(season, round_number, session_type, data)
    return data or {}


# ── Race-specific loaders (backward compatibility) ────────

@st.cache_resource(show_spinner="Loading race session...")
def get_race_session(season: int, round_number: int):
    return get_session(season, round_number, "R")


@st.cache_data(show_spinner="Parsing race data...")
def get_race_data(season: int, round_number: int) -> dict[str, DriverSessionData]:
    return get_session_data(season, round_number, "R")


@st.cache_data(show_spinner="Parsing qualifying data...")
def get_quali_data(season: int, round_number: int) -> dict[str, DriverSessionData]:
    return get_session_data(season, round_number, "Q")


# ── Ratings ───────────────────────────────────────────────

@st.cache_data(show_spinner="Computing driver ratings...")
def get_ratings(
    season: int,
    round_number: int,
) -> dict[str, DriverRating]:
    race_data  = get_race_data(season, round_number)
    quali_data = get_quali_data(season, round_number)

    quali_scores = None
    if quali_data:
        raw_quali    = score_qualifying_perf(quali_data)
        quali_scores = {
            code: raw_quali[code]
            for code in race_data
            if code in raw_quali
        }

    session = get_race_session(season, round_number)
    info    = get_session_info(session)
    return compute_race_ratings(race_data, session_info=info, quali_scores=quali_scores)


# ── Strategy ──────────────────────────────────────────────

@st.cache_data(show_spinner="Building strategy reports...")
def get_strategy_reports(
    season: int,
    round_number: int,
) -> dict[str, DriverStrategyReport]:
    race_data = get_race_data(season, round_number)
    session   = get_race_session(season, round_number)
    info      = get_session_info(session)
    return build_strategy_reports(race_data, session, info)


# ── Driver DNA ────────────────────────────────────────────

@st.cache_data(show_spinner="Building driver DNA profiles...")
def get_dna_data(season: int, round_number: int):
    from f1pitwall.driver_dna import (
        build_dna_vectors, cluster_drivers,
        build_similarity_ranking, build_dna_profiles,
        find_optimal_clusters,
    )
    race_data  = get_race_data(season, round_number)
    quali_data = get_quali_data(season, round_number)

    dna_vectors = build_dna_vectors(race_data, quali_data or None)
    _, inertias = find_optimal_clusters(dna_vectors)
    clustering  = cluster_drivers(dna_vectors, n_clusters=4)
    similarity  = build_similarity_ranking(dna_vectors)
    profiles    = build_dna_profiles(dna_vectors, clustering, similarity)

    return dna_vectors, clustering, similarity, profiles, inertias


# ── Schedule ──────────────────────────────────────────────

@st.cache_data(show_spinner="Loading schedule...")
def get_schedule(season: int):
    from f1pitwall.data_pipeline import list_rounds
    return list_rounds(season)