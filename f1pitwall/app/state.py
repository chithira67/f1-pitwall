# f1pitwall/app/state.py
"""
Centralised session state for Streamlit.
Loads and caches all data so components don't reload independently.
"""
import streamlit as st
from f1pitwall.data_pipeline import (
    load_session, get_session_info,
    parse_all_drivers, save_parsed_session, load_parsed_session,
)
from f1pitwall.scoring_engine import compute_race_ratings
from f1pitwall.scoring_engine.qualifying_perf import score_qualifying_perf
from f1pitwall.strategy_simulator import build_strategy_reports
from f1pitwall.models.session import SessionInfo
from f1pitwall.models.driver import DriverSessionData
from f1pitwall.scoring_engine.compositor import DriverRating
from f1pitwall.strategy_simulator.strategy_report import DriverStrategyReport


@st.cache_resource(show_spinner="Loading FastF1 session...")
def get_race_session(season: int, round_number: int):
    return load_session(season, round_number, "R", load_telemetry=True)


@st.cache_resource(show_spinner="Loading qualifying session...")
def get_quali_session(season: int, round_number: int):
    try:
        return load_session(season, round_number, "Q", load_telemetry=False)
    except Exception:
        return None


@st.cache_data(show_spinner="Parsing driver data...")
def get_race_data(season: int, round_number: int) -> dict[str, DriverSessionData]:
    data = load_parsed_session(season, round_number, "R")
    if not data:
        session = get_race_session(season, round_number)
        data = parse_all_drivers(session)
        if data:
            save_parsed_session(season, round_number, "R", data)
    return data or {}


@st.cache_data(show_spinner="Parsing qualifying data...")
def get_quali_data(season: int, round_number: int) -> dict[str, DriverSessionData]:
    data = load_parsed_session(season, round_number, "Q")
    if not data:
        session = get_quali_session(season, round_number)
        if session is None:
            return {}
        data = parse_all_drivers(session)
        if data:
            save_parsed_session(season, round_number, "Q", data)
    return data or {}


@st.cache_data(show_spinner="Computing driver ratings...")
def get_ratings(
    season: int,
    round_number: int,
) -> dict[str, DriverRating]:
    race_data = get_race_data(season, round_number)
    quali_data = get_quali_data(season, round_number)

    quali_scores = None
    if quali_data:
        raw_quali = score_qualifying_perf(quali_data)
        quali_scores = {
            code: raw_quali[code]
            for code in race_data
            if code in raw_quali
        }

    session = get_race_session(season, round_number)
    info = get_session_info(session)
    return compute_race_ratings(race_data, session_info=info, quali_scores=quali_scores)


@st.cache_data(show_spinner="Building strategy reports...")
def get_strategy_reports(
    season: int,
    round_number: int,
) -> dict[str, DriverStrategyReport]:
    race_data = get_race_data(season, round_number)
    session = get_race_session(season, round_number)
    info = get_session_info(session)
    return build_strategy_reports(race_data, session, info)


@st.cache_data(show_spinner="Loading schedule...")
def get_schedule(season: int):
    from f1pitwall.data_pipeline import list_rounds
    return list_rounds(season)