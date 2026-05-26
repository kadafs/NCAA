# Fix Dual Model Architecture: Eliminate Redundant SRS Duplication

## Problem
Non-Proballers leagues currently generate **two different score-based predictions**:
- `Model:169.1` — from `bball_stats_{id}.json` (API-Basketball standings → simple PPG averages)
- `SRS:195.8` — from `srs_stats_{id}.json` (merged Flashscore+API historical → iterative SRS algorithm)

These are fundamentally the same type of model (score-based), just with different math. The user's original design was:
- **Advanced Model** = Proballers detailed box scores (rebounds, turnovers, shooting %)
- **SRS Model** = Historical score-based Simple Rating System

When no Proballers data exists, the SRS model should be the **sole** model — not a secondary comparison alongside a weaker API-standings model.

## Proposed Changes

### `run_basketball_daily.py`

#### Current flow (broken):
1. `get_or_fetch_stats()` loads `bball_stats_{id}.json` → primary `Model:` total
2. `get_srs_stats()` loads `srs_stats_{id}.json` → secondary `SRS:` total
3. Both always run, producing two totals even when both are score-based

#### New flow (correct):
1. Check if `bball_stats_{id}.json` has `model_architecture == "[ADVANCED]"` (Proballers data)
2. **If ADVANCED**: Use Proballers stats for primary `Model:` total, show `SRS:` as secondary comparison
3. **If NOT ADVANCED** (i.e. `[  SRS   ]`): Use `srs_stats_{id}.json` as the **primary** `Model:` total. Do NOT show a secondary `SRS:` — there is only one model for this league
4. If neither exists → skip the league

#### Console output change:
- **Proballers league**: `Model:161.8 | SRS:158.2` (two different model types)
- **Non-Proballers league**: `Model:169.1` (SRS is the only model, no secondary)

### Files Modified
- [MODIFY] [run_basketball_daily.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/run_basketball_daily.py)

## Verification
- Run `python run_basketball_daily.py --league_id 57` → should show only one total (SRS-based)
- Run `python run_basketball_daily.py --league_id 198` → should show `Model:X | SRS:Y` (Proballers + SRS)
