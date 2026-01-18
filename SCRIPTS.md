# 📋 Project Scripts Reference Guide

This document provides a comprehensive map of all available scripts in the repository, organized by sport and function.

---

## 🧠 Core Framework (The Unified "Brain")
These shared scripts handle the statistical heavy lifting across all leagues:
- **[core/basketball_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/basketball_engine.py)**: The deterministic math engine. Handles Pace pivots, Efficiency scaling, and Situational Dampeners.
- **[core/prop_engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/prop_engine.py)**: The "Visual Authority" engine. Projects Pts/Reb/Ast using Usage Vacuum and Defensive Funnel logic.
- **[core/data_bridge.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/data_bridge.py)**: Standardizes raw JSON data from all leagues into a unified input sheet.
- **[core/universal_bridge.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/core/universal_bridge.py)**: The primary API bridge. Connects Python engines to the Next.js frontend.

## 🏀 NBA Scripts (National Basketball Association)

### The v1.2 Masterplan Engine (Deterministic)
The following scripts implement the **NBA PPG+PED Hybrid Totals v1.2** system:
- **[nba/v1_2/run_ultimate.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/v1_2/run_ultimate.py)**: **Recommended.** Unified NBA Dashboard featuring Totals + Prop Predictions with Usage Redistribution.
    - `--mode safe`: Stats-only projections.
    - `--mode full`: Adds injuries, fatigue, and usage redistribution.
    - `--trace`: Shows the full logic audit (Form weighting, Funnels, etc.).
- **[nba/v1_2/run.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/v1_2/run.py)**: Focuses strictly on game totals.
- **[nba/v1_2/engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/v1_2/engine.py)**: The core deterministic math logic for NBA.
- **[nba/v1_2/populate.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/v1_2/populate.py)**: NBA data bridge (Matchups, Stats, Injuries).

### Data Fetchers
- **[nba/fetch_nba_schedule.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/fetch_nba_schedule.py)**: Fetches today's NBA scoreboard and matchups.
- **[nba/fetch_nba_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/fetch_nba_stats.py)**: Fetches advanced team metrics (Four Factors, Pace, Ortg/Drtg).
- **[nba/fetch_nba_player_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/fetch_nba_player_stats.py)**: Fetches season averages for active players (for props).
- **[nba/fetch_nba_injuries.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/fetch_nba_injuries.py)**: Scrapes real-time injury notes from Action Network.

### Prediction Engines
- **[nba/predict_nba_full.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/predict_nba_full.py)**: **Recommended.** The all-in-one dashboard including Scores, Spreads, Injuries, and Prop Trends.
- **[nba/predict_advanced_nba.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/predict_advanced_nba.py)**: Pure efficiency-based game model.
- **[nba/predict_simple.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/nba/predict_simple.py)**: Simple PPG-based scoring model for manual analysis.

---

## 🎓 NCAA Scripts (College Basketball)

### The v1.2 Masterplan Engine (Deterministic)
The following scripts implement the **PPG+PED Hybrid Totals v1.2** system:
- **[ncaa/v1_2/run.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/v1_2/run.py)**: Main entry point for v1.2 totals analysis.
    - `--mode safe`: Runs pure statistical math.
    - `--mode full`: Runs stats + injury context.
    - `--refresh`: Auto-runs all fetchers before predicting.
- **[ncaa/v1_2/engine.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/v1_2/engine.py)**: The core deterministic math logic.
- **[ncaa/v1_2/populate.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/v1_2/populate.py)**: Auto-populates daily matchups and stats.

### Data Fetchers & Processors
- **[ncaa/data_fetcher.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/data_fetcher.py)**: Fetches team and individual NCAA stats from internal APIs.
- **[ncaa/fetch_injuries.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/fetch_injuries.py)**: Scrapes NCAA injury notes from Action Network.
- **[ncaa/assemble_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/assemble_stats.py)**: Consolidates BartTorvik CSV chunks into usable JSON.

### Legacy/Specific Prediction Models
- **[ncaa/predict_advanced.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_advanced.py)**: Advanced tempo/efficiency game model.
- **[ncaa/predict_totals.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_totals.py)**: Specialized for Over/Under betting.
- **[ncaa/predict_props.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/ncaa/predict_props.py)**: Generates player prop baseline projections.

---

## 🇪🇺 EuroLeague Scripts (v1.9 Expansion)
The newest module for tracking European elite competition:
- **[euro/fetch_euro_schedule.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/euro/fetch_euro_schedule.py)**: Fetches matchups from the official v1 Results API.
- **[euro/fetch_euro_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/euro/fetch_euro_stats.py)**: Fetches advanced team metrics (Possessions, Off/Def Ratings).
- **[euro/fetch_euro_player_stats.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/euro/fetch_euro_player_stats.py)**: Fetches seasonal averages for 700+ Euro players.
- **[euro/v1_2/populate.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/euro/v1_2/populate.py)**: Bridges Euro stats into the v1.2 engine.
- **[euro/predict_simple.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/euro/predict_simple.py)**: Simple PPG-based scoring model for manual analysis.

## 🛠️ Shared Utilities
- **[utils/mapping.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/utils/mapping.py)**: Shared logic for team name cleaning, aliases, and NBA tricodes.

---

## ⚡ Quick Execution Commands

### 🌟 Primary Tool (Universal Framework v1.4)

Recommended for all league analysis (NBA, NCAA, Euro).

| Command | Purpose |
| :--- | :--- |
| `python run_universal.py --league nba --mode full --trace` | **NBA Ultimate Dashboard** (Totals + Props) |
| `python run_universal.py --league ncaa --mode safe --trace` | **NCAA Totals Prediction** |
| `python run_universal.py --league euro --mode safe --trace` | **EuroLeague Totals + Props** |

---

## 🏀 NBA Prediction Tools (v1.2 Legacy)
```powershell
python nba/predict_nba_full.py
```
