# D1 Conference-Only Prediction Workflow

This document outlines the complete workflow for generating and auditing NCAA Division 1 basketball predictions using **conference-only statistics**.

---

## Overview

The D1 conference-only prediction system uses pure conference game statistics from Barttorvik to generate totals predictions. This approach isolates conference performance from non-conference games, providing more accurate predictions for conference matchups.

---

## Workflow Steps

### 1. Fetch Conference-Only Statistics

**Script:** `ncaa/fetch_barttorvik_conf.py`

**Purpose:** Download the latest conference-only statistics from Barttorvik (using `conflimit=1` parameter)

**Command:**
```bash
python ncaa/fetch_barttorvik_conf.py
```

**Output:**
- `data/barttorvik_stats_conf.json` - Processed conference-only stats
- `data/barttorvik_raw_conf.json` - Raw fallback data

**Data Sources (in priority order):**
1. Centralized API: `https://ncaa-api-w2ry.onrender.com/stats/barttorvik/conf`
2. Direct scrape: `https://barttorvik.com/trank.php?year=2026&csv=1&conflimit=1`
3. Cached fallback: `data/barttorvik_raw_conf.json`

**Key Stats Fetched:**
- `adj_off` - Adjusted Offensive Efficiency (conference games only)
- `adj_def` - Adjusted Defensive Efficiency (conference games only)
- `adj_t` - Adjusted Tempo (conference games only)
- Four Factors: `efg`, `to`, `or`, `ftr` (offense & defense)
- `conf` - Conference affiliation

---

### 2. Generate Predictions

**Script:** `ncaa/predict_d1_conf.py`

**Purpose:** Generate game predictions using conference-only statistics

**Commands:**
```bash
# Safe mode (conservative betting thresholds)
python ncaa/predict_d1_conf.py --mode safe

# Full mode (includes injury adjustments)
python ncaa/predict_d1_conf.py --mode full

# Show detailed calculation trace
python ncaa/predict_d1_conf.py --mode safe --trace

# Specify a different date
python ncaa/predict_d1_conf.py --mode safe --date 2026-02-15
```

**Prediction Modes:**
- **safe**: Conservative thresholds, no injury data (default)
- **full**: Includes injury adjustments from `data/injury_notes.json`

**Output:**
- `data/d1_conf_predictions.json` - All predictions with decisions
- Terminal output showing each game's prediction

**Decision Types:**
- **PLAY** - High confidence bet (Mode A or B with strong edge)
- **LEAN** - Lower confidence bet (edge exists but below PLAY threshold)
- **PASS** - No bet recommended (edge too small)

**What It Does:**
1. Loads conference-only stats from `data/barttorvik_stats_conf.json`
2. Fetches today's D1 scoreboard
3. For each game:
   - Matches teams to conference-only stats
   - Retrieves market total from odds API
   - Calculates model total using `UniversalBasketballEngine`
   - Determines edge (model total - market total)
   - Makes betting decision based on edge thresholds
4. Saves all predictions to JSON file

---

### 3. Audit Performance

**Script:** `ncaa/audit_performance.py`

**Purpose:** Grade predictions against actual game results

**Commands:**
```bash
# Audit PLAY/LEAN decisions only
python ncaa/audit_performance.py

# Include PASS decisions in audit
python ncaa/audit_performance.py --include-pass

# Audit specific predictions file
python ncaa/audit_performance.py --file data/d1_conf_predictions.json

# Audit specific date
python ncaa/audit_performance.py --date 2026-02-14
```

**What It Does:**
1. Loads predictions from JSON file
2. Fetches live scores for the prediction date
3. Matches predictions to actual games
4. Grades each prediction:
   - **WIN**: Bet would have won
   - **LOSS**: Bet would have lost
   - **PUSH**: Exact tie with market line
   - **GOOD PASS**: Correctly avoided a losing bet (with `--include-pass`)
   - **BAD PASS**: Missed a winning opportunity (with `--include-pass`)
5. Displays results table with:
   - Matchup
   - Prediction type (OVER/UNDER/PASS_OVER/PASS_UNDER)
   - Model total
   - Market line
   - Actual score
   - Result
6. Shows summary statistics (wins, losses, win rate)

---

## Complete Daily Workflow

### Morning Routine (Before Games Start)

```bash
# Step 1: Update conference-only statistics
python ncaa/fetch_barttorvik_conf.py

# Step 2: Generate today's predictions
python ncaa/predict_d1_conf.py --mode safe

# Optional: Review predictions with trace
python ncaa/predict_d1_conf.py --mode safe --trace
```

### Evening Routine (After Games Complete)

```bash
# Step 3: Audit yesterday's predictions
python ncaa/audit_performance.py

# Optional: Include PASS decisions to evaluate conservativeness
python ncaa/audit_performance.py --include-pass
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────┐
│  Barttorvik Conference-Only Stats   │
│  (conflimit=1)                      │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  fetch_barttorvik_conf.py           │
│  Downloads & processes stats        │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  data/barttorvik_stats_conf.json    │
│  Conference-only team statistics    │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  predict_d1_conf.py                 │
│  • Loads conference stats           │
│  • Fetches today's games            │
│  • Gets market odds                 │
│  • Calculates model totals          │
│  • Makes betting decisions          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  data/d1_conf_predictions.json      │
│  All predictions with decisions     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  audit_performance.py               │
│  • Loads predictions                │
│  • Fetches final scores             │
│  • Grades each prediction           │
│  • Calculates win rate              │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  Performance Report                 │
│  Win/Loss record & statistics       │
└─────────────────────────────────────┘
```

---

## Key Configuration Files

### NCAA League Config
**File:** `configs/leagues/ncaa.json`

Contains betting thresholds and model parameters:
- Edge thresholds for PLAY/LEAN decisions
- Regression floors
- Safety rules
- Conference bias adjustments

### Injury Data (Full Mode Only)
**File:** `data/injury_notes.json`

Optional injury information for full mode predictions.

---

## Important Notes

### Conference-Only vs Full Season Stats

**Conference-Only (This System):**
- ✅ Pure conference game performance
- ✅ More relevant for conference matchups
- ✅ Isolates true conference strength
- ❌ Limited data for teams with few conference games

**Full Season (Other Systems):**
- ✅ More data points
- ✅ Works for all games
- ❌ Includes non-conference cupcake games
- ❌ Can skew efficiency ratings

### Why Conference-Only?

Conference games are typically:
- More competitive
- Better coached
- More familiar matchups
- More predictive of future conference performance

### Data Freshness

- **Barttorvik stats**: Updated daily after games complete
- **Scoreboard data**: Real-time from NCAA API
- **Odds data**: Real-time from centralized odds API

### Troubleshooting

**No predictions generated:**
- Check if `data/barttorvik_stats_conf.json` exists
- Verify teams are in the conference-only dataset
- Some teams may not have enough conference games played

**Audit shows "Not Found":**
- Game may not be in the scoreboard API (too old or future game)
- Team name mismatch between prediction and scoreboard
- Run audit on the same day or day after predictions

**Many NaN predictions:**
- Teams don't have conference-only stats yet
- Early in the season before conference play starts
- Teams from smaller conferences not in Barttorvik dataset

---

## Example Output

### Prediction Output
```
[GAME] MATCHUP: UCLA @ Michigan
   Market: 156.5 | Model: 141.8 | Edge: -14.72 | [A] PLAY

   Conference-Only Advanced Metrics:
     [Away] Stats: AdjT 66.5 | OE: 127.3 | DE: 103.3 | eFG: 56.4 | TO: 13.7 | OR: 26.0 | FTR: 32.9
     [Home] Stats: AdjT 65.4 | OE: 133.4 | DE: 99.7 | eFG: 55.0 | TO: 13.3 | OR: 36.8 | FTR: 34.7
```

### Audit Output
```
====================================================================================================
MATCHUP                             | PRED       | MODEL  | LINE   | SCORE    | RESULT    
----------------------------------------------------------------------------------------------------
UCLA @ Michigan                     | UNDER      | 141.8  | 156.5  | 142      | WIN
Northwestern @ Nebraska             | UNDER      | 135.4  | 146.0  | 117      | WIN
----------------------------------------------------------------------------------------------------
AUDIT COMPLETE
Wins: 17 | Losses: 9 | Pending: 0
Win Rate: 65.4%
```
