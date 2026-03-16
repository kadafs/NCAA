---
description: Daily Football BTTS + Draw prediction workflow
---
# Football Prediction Workflow

## Universal Runner (All Leagues — Recommended)

Runs predictions for **every football league** active today in a single command:

```bash
python run_football_daily.py                    # all leagues today (safe mode)
python run_football_daily.py --mode full        # sharp layer on
python run_football_daily.py --league_id 39     # EPL only
python run_football_daily.py --min_games 2      # skip leagues with < 2 games
python run_football_daily.py --date 2026-03-15  # past date (backtesting)
```

Output: `data/football/universal_predictions_YYYY-MM-DD.json`

---

## Per-League Runner (Hand-Tuned Leagues)

This workflow covers the daily execution of the Football BTTS (Both Teams to Score) and Draw prediction models. Currently supported leagues: `epl`, `la_liga`, `bundesliga`, `serie_a`, `ligue_1`, `a_league`.

> [!IMPORTANT]
> The API-Football (api-sports.io) key must be on a paid tier (Pro or above) to access current season live fixtures.

## 1. The Daily Run

**Yes, a single command per league is enough.**

Run this command for each league you want to predict today. Ensure you include the `--refresh` flag on your **first run of the day** so that the model downloads today's fixtures and updates team stats/form.

```bash
# Example: Running La Liga today
python run_universal.py --league la_liga --sport football --mode full --refresh --trace
```

### Why this is enough:
The `--refresh` flag automatically calls:
1. `fetch_football_schedule.py`: Gets the live fixtures for today.
2. `fetch_football_stats.py`: Gets the latest attack/defense ratings, clean sheet rates, and form strings for every team.
3. The engine then immediately runs the Poisson math against those fresh stats.

*(Note: The `--sport football` flag is optional if using a known football league code like `la_liga`, as the router auto-detects it, but it's good practice to include it).*

## 2. Follow-Up Runs (Same Day)

If you need to re-run the prediction later in the day (e.g. to try Safe mode instead, or to check the trace output again), **drop the `--refresh` flag**.

This prevents you from burning unnecessary API requests, since the fixtures and stats for today are already cached locally.

```bash
# Re-running without burning API calls
python run_universal.py --league la_liga --mode safe --trace
python run_universal.py --league la_liga --mode full --trace
```

## 3. Interpreting the Output

The football engine outputs probabilities, not total scores.

### BTTS (Primary Market)
Look for the **BTTS Edge** and **Decision**.
- `PLAY YES [HIGH]`: Model says Both Teams to Score is highly likely (edge > 8%).
- `PLAY YES [MEDIUM]`: Model sees value on BTTS Yes (edge > 4%).
- `PLAY NO`: Model says BTTS is unlikely (edge < -4%).
- `PASS [NO PLAY]`: Model probability matches the bookmaker's implied probability. No edge.

### Draw (Secondary Market)
Draws are much harder to hit, so the model provides **Fair Odds** instead of a hard Play/Pass decision.
- Look at the `Fair Odds` output (e.g., `3.73x`).
- Check your sportsbook. If they are offering **higher** odds than the model's Fair Odds (e.g., they offer +300 / 4.00x), there is mathematical value on the Draw.
- The model will explicitly append `← Check draw market` if the game is a BTTS PASS but has a healthy draw probability.

## 4. API Rate Limits (Important)

Your `API_BASKETBALL_KEY` works for this, but keep an eye on your 100 requests/day limit if on a low-tier plan.

A single `--refresh` for a football league costs:
- 1 request for the schedule
- 20 requests for the team stats (1 per team)
- **Total: ~21 requests per league.**

You can comfortably refresh 4 leagues a day on a 100 req/day plan. Do not run `--refresh` multiple times per day for the same league.
