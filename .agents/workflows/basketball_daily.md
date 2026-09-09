---
description: Daily universal basketball predictions for all api-basketball.com leagues
---

# Daily Basketball Prediction Workflow

Runs predictions for ALL basketball leagues available via api-basketball.com today, excluding NBA/NCAA/NBL/NBL1 which are covered by their own dedicated scripts.

## Prerequisites

- `.env` file with `API_BASKETBALL_KEY` set
- At least one `data/api_basketball_today_*.json` cache file (from a previous run or from `explore_api_basketball_today.py`)

---

## Step 1 — Fetch today's fixtures

Fetches all live games for today into a local cache file.

```bash
python explore_api_basketball_today.py
```

Output: `data/api_basketball_today_YYYY-MM-DD.json`

> **Note:** This is the primary data source for team stats too. Run daily to accumulate historical scores.

---

## Step 1.5 — Update Advanced Form (Proballers)

Run the mass batch extractor for active leagues today (or pass `--file configs/proballers_leagues.txt`) to fetch the most recent data points and recalibrate True Offense/Defense metrics.

```bash
python scrape_proballers.py --daily today
python generate_advanced_metrics.py
python generate_advanced_metrics_v2.py
```

---

## Step 2 — Run predictions

```bash
python run_basketball_daily.py
```

**Options:**
```bash
python run_basketball_daily.py --mode full          # enable sharp layer
python run_basketball_daily.py --league_id 251      # single league
python run_basketball_daily.py --min_games 3        # only leagues with 3+ games
python run_basketball_daily.py --refresh            # re-fetch fixtures from API
python run_basketball_daily.py --trace              # show engine math trace
python run_basketball_daily.py --no_calibrate       # skip auto-calibration
```

Output:
- Console: matchup-by-matchup model totals
- File: `data/basketball_predictions_YYYY-MM-DD.json`

---

## Step 3 — (Optional) Pre-calibrate a specific league

If you want to force a tier or pre-calibrate before running predictions:

```bash
python calibrate_league.py --league_id 40                   # auto-calibrate BBL
python calibrate_league.py --league_id 40 --tier top_domestic  # force tier
python calibrate_league.py --all                            # calibrate all leagues from today
python calibrate_league.py --list_tiers                     # show all tier templates
```

Output: `configs/leagues/<league_id>.json`

---

## How Stats Accumulate (Free Tier)

The free API tier does not allow historical season queries. Instead, team stats are derived from the accumulated `data/api_basketball_today_*.json` files:

- Day 1: stats from only today's finished games (low sample, high regression)
- Week 1: 7 days × ~5 games/team = reasonable estimate
- Month 1: reliable ratings for any league with daily games

Run the workflow daily and accuracy improves automatically.

---

## Excluded Leagues (Handled by Dedicated Scripts)

| League | Script |
|--------|--------|
| NBA    | `run_universal.py --league nba` |
| NCAA   | `run_universal.py --league ncaa` |
| NBL    | `run_universal.py --league nbl` |
| NBL1   | `run_universal.py --league nbl1` |
