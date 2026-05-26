# Conference-Only Stats Models Implementation

## ⚠️ Update: D1 Only - D2 Not Ready

After implementation review, only D1 is ready for testing. D2 requires game-by-game schedule parsing.

---

## Phase 1: Data Layer
- [x] Create `fetch_barttorvik_conf.py` for D1 conference-only stats
- [x] Document `data_fetcher_conf.py` as D2 placeholder (not ready)
- [x] Test D1 data fetching

## Phase 2: Prediction Models
- [x] Create `predict_d1_conf.py` using PURE Barttorvik conference data
- [x] Document `predict_d2_conf.py` as not ready (exits with error)
- [x] Validate D1 model runs without errors

## Phase 3: Testing Infrastructure
- [x] Create `compare_models.py` for side-by-side comparison (D1 only)
- [x] Create `backtest_conf_models.py` for historical validation (D1 only)
- [x] Update logging structure for D1 predictions

## Phase 4: Validation & Documentation
- [x] Run initial D1 test predictions (Data workflow established)
- [x] Document D1 usage and testing procedures
- [x] Document D2 limitations and future requirements
- [x] Create performance tracking system

## Phase 5: Future D2 Enhancement (Deferred)
- [ ] Fetch game-by-game schedules for D2 teams
- [ ] Parse conference opponent identification
- [ ] Recalculate stats from conference games only
- [ ] Implement true D2 conference filtering

---

## Key Implementation Details

### D1 Model ✅ COMPLETE
- Uses ONLY Barttorvik conference stats (`&conflimit=1`)
- No mixing with NCAA.com data
- Model structure validated and running
- Output format: `d1_conf_predictions.json`
- Supports `safe` and `full` modes

### D2 Model ⚠️ DEFERRED
- Documented as placeholder
- Exits with clear error message
- Requires game-by-game schedule parsing
- Deferred for future phase

---

## Testing Plan (D1 Only)

1. **Daily Execution**
   - Run `python ncaa/fetch_barttorvik_conf.py` daily
   - Run `python ncaa/predict_d1_conf.py --mode full` daily
   - Track predictions in `data/d1_conf_predictions.json`

2. **Weekly Comparison**
   - Run `python compare_models.py --division d1 --mode full`
   - Compare MAE and hit rate vs full-season model
   - Analyze tier performance

3. **Decision Point (2-3 weeks)**
   - If conference-only wins: Switch permanently
   - If full-season wins: Keep current approach
   - If mixed: Consider weighted blending
