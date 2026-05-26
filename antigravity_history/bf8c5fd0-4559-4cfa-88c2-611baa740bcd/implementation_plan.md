# Football V2: Predictive Engine & Grading Upgrade

This document outlines an end-to-end upgrade for the football pipeline, solving the critical sample-size issues in early-season/international predictions, and overhauling the post-match tracking system to match basketball's granular standards.

## Goal Description

Currently, the football prediction engine struggles with highly-volatile, small-sample-size games (like International Friendlies) and its post-match tracking is limited to simple binary Win/Loss hit rates. 

We will upgrade this to a **V2 Standard** by implementing advanced probabilistic smoothing (Bayesian Regression) for club games, introducing Elo Ranking systems for international fixtures, and adding a continuous Delta Grading Matrix to evaluate the model's accuracy on a granular level.

---

## Proposed Changes

### Phase 1: Predictive Engine Mathematics (`run_football_daily.py`)

#### Dynamic Bayesian Regression (Club Games)
- **Problem:** A 1-game winning streak currently commands an unearned `0.88` trust weighting from the engine, resulting in wildly inaccurate confidence early in the season.
- **Solution:** Implement a dynamic regression scalar based on the `played_all` integer. If `played_all` = 1, regression is ~`0.10` (90% league average). As games approach `10`, regression smoothly scales up to the maximum `0.88`.

#### International Elo integration (`country == "World"`)
- **Problem:** National teams don't play normal "seasons", rendering standard goals-scored stats obsolete.
- **Solution:** Build an independent logic path for "World" fixtures. Automatically fetch the live points difference between the generic team's FIFA/Elo rating, mathematically mapping the rating delta to home/away Expected Goals (xG), entirely ignoring the generic API-Sports seasonal tables constraint.

---

### Phase 2: Grading Matrices (`grade_football.py` & `aggregate_league_stats.py`)

#### Football Delta Grading Matrix
Instead of solely checking whether a BTTS or 1X2 bet won, evaluate the model's overall conceptual accuracy.
- Calculate **Absolute xG Delta**: `abs(actual_match_goals - predicted_match_goals)`
- Establish football tiers matching basketball's color-coded grading system:
  - `<= 0.50 goals diff`: 🎯 BULLSEYE
  - `<= 1.00 goals diff`: 🟢 EXCELLENT
  - `<= 1.50 goals diff`: 🟡 SOLID
  - `<= 2.00 goals diff`: 🟠 MISS
  - `> 2.00 goals diff`: 🔴 BUST

#### Team-Level Leaderboards & Signed Delta Bias
- Extend `aggregate_league_stats.py` to output a `football_team_leaderboard.json`, highlighting exactly which clubs are consistently profitable vs. chaotic bankroll-drainers.
- Track `avg_signed_delta` on both leagues and teams to diagnose if the model chronically overestimates or underestimates a specific league's scoring rate.

#### Baseline Epoch Setup
- Add `TRACKING_EPOCH = "2026-03-26"` so that when this V2 engine goes live, our leaderboards only aggregate the newly optimized mathematical predictions, freezing legacy predictions out of the tracked MAPE/Hit Rates.

---

## Open Questions / User Review Required

> [!WARNING]
> Integration with Elo Ratings requires finding a reliable, free data source or API for international team rankings since the standard API-Sports football library doesn't output Elo natively. Would you prefer we write a scraper for something like `eloratings.net`, or use the official `FIFA World Rankings` which the api-football service *might* have buried in it?

> [!IMPORTANT]
> The Delta Grading Matrix requires the model to have a rigid `predicted_total_goals` value. `run_football_daily.py` currently outputs `xg_home` and `xg_away` which sums to `xg_total`. We will use this `xg_total` as the anchor for the Delta matrix vs the actual match goals. Does this sound correct?
