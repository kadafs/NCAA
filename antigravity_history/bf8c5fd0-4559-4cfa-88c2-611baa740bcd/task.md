# Football V2 Upgrade Tasks

- `[x]` **Phase 1: Predictive Engine Mathematics (`run_football_daily.py`)**
  - `[x]` Implement Dynamic Bayesian Regression (scale `min_req` and `regression` based on `played_all`).
  - `[x]` Setup static JSON Elo map fallback (`elo_ratings.json`) because of cloudflare/SSL blocking the API environment locally.
  - `[x]` Build Elo to xG conversion logic for international matchups (`calc_xg_elo`).
- `[x]` **Phase 2: Grading Matrices (`grade_football.py` & `aggregate_league_stats.py`)**
  - `[x]` Add Delta Grading Matrix to `grade_football.py` (Actual Goals vs `xg_total`).
  - `[x]` Update json output with `accuracy_tier`, `total_delta`, `signed_delta`.
  - `[x]` Modify `aggregate_league_stats.py` to compile MAE and signed delta metrics.
  - `[x]` Implement `football_leaderboard.json` tracking for Team-level analytics.
  - `[x]` Setup `TRACKING_EPOCH = "2026-03-26"` freeze logic.
- `[x]` **Phase 3: Verify**
  - `[x]` Ran full scale aggregator tests (3 valid files correctly parsed into both leaderboards).
  - `[x]` Test prediction script execution logic manually.
