# Walkthrough: SRS Parallel Prediction Model

This walkthrough documents the successful integration of a Simple Rating System (SRS) prediction model that runs in parallel with the existing Advanced (Proballers) model.

## Key Accomplishments

### 1. SRS Stats Builder
- Created `build_srs_stats.py` to derive `adj_off`, `adj_def`, and `adj_t` metrics directly from historical game results (`data/historical/api_basketball_{id}.json`).
- Iteratively computes team SRS ratings to account for strength of schedule.
- Successfully generated `srs_stats_{id}.json` for **102 leagues** that have existing historical data.

### 2. Parallel Engine Execution
- Modified `run_basketball_daily.py` to run both models side-by-side.
- The Advanced model continues to be the primary output, with SRS predictions embedded as a hidden `"srs"` block in the JSON record.
- This allows for side-by-side accuracy comparison in the future without disrupting the current frontend display.

### 3. Automated Data Pipeline
- Integrated `build_srs_stats.py` into the daily update flow. It now runs automatically at the end of `auto_update_historical.py` to ensure SRS ratings incorporate the latest scores.

## Data Structure Example

Predictions now include an embedded SRS block for comparison:

```json
{
  "model_total": 218.4,
  "model_architecture": "[ADVANCED]",
  "srs": {
    "model_total": 221.0,
    "xpts_h": 112.5,
    "xpts_a": 108.5,
    "predicted_result": "HOME",
    "source": "SRS"
  }
}
```

## Push to GitHub
All code changes and initial SRS data files have been committed and pushed to the repository.

- **Commits:**
  - `48f9d86`: Add SRS parallel model scripts and wiring.
  - `f1389ae`: Update basketball stats and add 269 data files.
