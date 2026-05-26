# Historical Basketball Grading Plan (March 26-29)

The current `grade_basketball.py` script is unable to fetch scores for dates older than 24 hours due to API tier limitations. We need a workaround to populate the `Universal Predictions` JSON files for March 26th through 29th so that the Delta Grading Matrix and Leaderboards can be updated.

## User Review Required

> [!IMPORTANT]
> This plan relies on **Proballers** data as the primary source for historical scores. We will use `scrape_proballers.py` to fetch the missing games first, then inject them into the predictions.

## Proposed Changes

### [Component 1] Data Acquisition (Proballers)

We will run the existing `scrape_proballers.py` script for the relevant leagues to ensure the latest games (from March 26-30) are cached locally in `data/historical/proballers_*.json`.

### [Component 2] Fallback Grading Script

I will create a temporary utility script `grade_from_proballers.py` that:
1. Loads a target `universal_predictions_YYYY-MM-DD.json`.
2. For each ungraded prediction, searches the `data/historical/proballers_*.json` files for a matching team pair and date.
3. If a match is found, captures the `home_score` and `away_score`.
4. Saves the updated predictions.

### [Component 3] Execution & Aggregation

Once the predictions are graded:
1. Run `python grade_basketball.py --regrade --date <DATE>` for each date to calculate the Delta Matrix (BULLSEYE, SOLID, etc.) using the newly injected scores.
2. Run `python aggregate_basketball_stats.py` to update the global leaderboards.
3. Push everything to the dashboard using `push_to_dashboard.py`.

## Open Questions

- Should I prioritize specific leagues first, or run the entire `proballers_leagues.txt` list? (Running all might take some time due to rate limiting).

## Verification Plan

### Manual Verification
- Check `data/basketball/universal_predictions_*.json` for correctly populated `actual_result` and `total_delta` fields.
- Verify that the `league_leaderboard.json` reflects the new historical data.
- Confirm dashboard deployment.
