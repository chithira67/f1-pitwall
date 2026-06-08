# 🏎 F1 Pitwall

> A Formula 1 analytics platform built on FastF1 telemetry data — driver performance ratings, race strategy simulation, live telemetry visualisation, and ML-powered driving style clustering.

![Python](https://img.shields.io/badge/Python-3.11+-3671C6?style=flat-square&logo=python&logoColor=white)
![FastF1](https://img.shields.io/badge/FastF1-3.8+-E8002D?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.33+-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?style=flat-square&logo=scikit-learn&logoColor=white)

---

## What it does

F1 Pitwall turns raw timing and telemetry data into structured, explainable insights — the kind of analysis that F1 performance engineers do after every race weekend.

| Module | What it produces |
|---|---|
| **Data Pipeline** | Typed, cached, validated session data for any race, qualifying, or practice session |
| **Driver Rating Engine** | 5-pillar composite scores (Race Craft, Pace, Tyres, Consistency, Qualifying) normalised across the field |
| **Strategy Simulator** | Pit window optimisation, undercut/overcut simulation, safety car luck index |
| **Live Dashboard** | Interactive Streamlit app — ratings, strategy, lap times, telemetry traces |
| **Driver DNA** | 8-dimensional identity vectors, KMeans clustering, PCA similarity map |

---

## Dashboard

### 📊 Driver Ratings
Composite performance scores across 5 weighted dimensions with radar chart comparison.

### 🏁 Strategy Overview
Tyre stint visualisation for the full field, pit stop timing verdicts (optimal / early / late), and safety car luck index.

### 📈 Lap Times
Multi-driver lap time chart with tyre compound colour coding and position-over-laps chart.

### 📡 Telemetry
Speed, throttle, and brake traces overlaid by distance for any lap — fastest lap by default.

### 🧬 Driver DNA
PCA-based driver similarity map, feature heatmap across all 8 dimensions, and per-driver style profile with most-similar-driver rankings.

---

## Quickstart

### 1. Clone the repo
```bash
git clone https://github.com/chithira67/f1-pitwall.git
cd f1-pitwall
```

### 2. Create a virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Launch the dashboard
```bash
streamlit run f1pitwall/app/main.py
```

The app opens at `http://localhost:8501`.  
FastF1 downloads and caches session data automatically on first load (~30s per session). Every subsequent load is instant from the local cache.

---

## Project Structure

```
f1-pitwall/
├── f1pitwall/
│   ├── config.py                   ← paths, settings
│   ├── data_pipeline/
│   │   ├── loader.py               ← FastF1 session loader
│   │   ├── parser.py               ← telemetry → typed domain models
│   │   └── cache.py                ← parsed JSON cache layer
│   ├── models/
│   │   ├── session.py              ← SessionInfo, SessionType
│   │   ├── lap.py                  ← LapData, TyreCompound
│   │   └── driver.py               ← DriverSessionData, StintSummary
│   ├── scoring_engine/
│   │   ├── race_craft.py           ← overtakes, position gain
│   │   ├── pace_efficiency.py      ← teammate delta, session delta
│   │   ├── tyre_management.py      ← degradation slope, stability
│   │   ├── qualifying_perf.py      ← Q1/Q2/Q3 teammate delta
│   │   ├── consistency.py          ← lap time variance
│   │   └── compositor.py           ← weighted composite score
│   ├── strategy_simulator/
│   │   ├── pit_analyser.py         ← optimal pit window, timing verdict
│   │   ├── undercut_sim.py         ← undercut/overcut simulation
│   │   ├── safety_car.py           ← SC/VSC luck index
│   │   └── strategy_report.py      ← combined report
│   ├── driver_dna/
│   │   ├── feature_builder.py      ← 8-dimensional identity vectors
│   │   ├── clustering.py           ← KMeans + PCA
│   │   ├── similarity.py           ← cosine similarity rankings
│   │   └── dna_report.py           ← driver style profiles
│   └── app/
│       ├── main.py                 ← Streamlit entry point
│       ├── state.py                ← cached data loaders
│       └── components/
│           ├── sidebar.py
│           ├── leaderboard.py
│           ├── radar_chart.py
│           ├── lap_chart.py
│           ├── strategy_view.py
│           ├── telemetry_view.py
│           └── dna_view.py
├── scripts/
│   ├── test_pipeline.py
│   ├── test_scoring.py
│   ├── test_strategy.py
│   ├── test_dashboard.py
│   └── test_dna.py
├── notebooks/
│   └── 2024_bahrain_analysis.ipynb
├── requirements.txt
└── pyproject.toml
```

---

## Running the test suite

```bash
python scripts/test_pipeline.py   # Phase 1 — data pipeline
python scripts/test_scoring.py    # Phase 2 — driver ratings
python scripts/test_strategy.py   # Phase 3 — strategy simulator
python scripts/test_dashboard.py  # Phase 4 — dashboard components
python scripts/test_dna.py        # Phase 5 — driver DNA + ML
```

---

## Sessions supported

| Session | Ratings | Strategy | Lap Times | Telemetry | Driver DNA |
|---|---|---|---|---|---|
| Race | ✅ | ✅ | ✅ | ✅ | ✅ |
| Sprint | ✅ | ✅ | ✅ | ✅ | ✅ |
| Qualifying | ✅ | — | ✅ | ✅ | — |
| Sprint Qualifying | ✅ | — | ✅ | ✅ | — |
| Practice 1/2/3 | — | — | ✅ | ✅ | — |

---

## Tech stack

| Tool | Purpose |
|---|---|
| [FastF1](https://github.com/theOehrly/Fast-F1) | F1 timing and telemetry data |
| [Pandas](https://pandas.pydata.org/) | Data manipulation |
| [NumPy](https://numpy.org/) | Numerical computing |
| [Pydantic](https://docs.pydantic.dev/) | Typed domain models |
| [scikit-learn](https://scikit-learn.org/) | KMeans clustering, PCA |
| [Plotly](https://plotly.com/python/) | Interactive charts |
| [Streamlit](https://streamlit.io/) | Dashboard framework |
| [SciPy](https://scipy.org/) | Linear regression for degradation slopes |
| [Rich](https://github.com/Textualize/rich) | Terminal output formatting |

---

## Data

All data is sourced via [FastF1](https://github.com/theOehrly/Fast-F1) which pulls from the official F1 timing feed and Ergast API. Sessions are cached locally after first load — the `data/` directory is gitignored.

Seasons available: **2018 onwards** (subject to FastF1 version).

---

## License

MIT