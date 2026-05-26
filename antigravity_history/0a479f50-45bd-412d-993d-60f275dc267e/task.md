# Task: SRS Parallel Model Integration

## Phase 1: Build SRS Stats Builder
- [x] Inspect how SRS stats are currently computed (fetch_universal_bball_stats.py)
- [x] Create `build_srs_stats.py` — reads historical API game files, computes SRS ratings, writes `srs_stats_{id}.json`
- [x] Verified: 102/102 leagues with historical data built successfully

## Phase 2: Expand League Tracking
- [x] Confirmed all 286 Proballers leagues are already in `league_slug_map.json` — no expansion needed

## Phase 3: Parallel Engine in run_basketball_daily.py
- [x] Added `get_srs_stats()` helper to load `srs_stats_{id}.json`
- [x] SRS engine runs in parallel after Advanced prediction
- [x] `srs` block embedded in prediction JSON (no frontend changes)

## Phase 4: Wire up Daily Updates
- [x] Added subprocess call to `build_srs_stats.py` at end of `auto_update_historical.py`

## Phase 5: Push and Verify
- [x] Push all changes to GitHub
- [x] Do a manual test run and confirm both models produce output
- [x] Created `export_predictions_to_csv.py` for easy data analysis
