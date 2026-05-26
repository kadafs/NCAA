# Confidence Engine Math Fix

## What Was Done

We discovered a critical flaw in the Confidence Scoring Engine where highly volatile teams were achieving `[HIGH]` confidence ratings because their terrible stats were being "averaged" out by elite opponents. 

### 1. Updated `core/confidence_score.py`
We changed the core math of the engine to grade games based on the **Worst Maximum** rather than the Average.
- **Volatility:** Changed from `avg_vol` to `max_vol`. The engine now takes the highest standard deviation of the two teams and grades the stability of the entire game on that number.
- **MAE:** Changed from `avg_mae` to `max_mae`. If the model is completely blind to one team, the game is now heavily penalized.
- **Bias:** Remained as an average, because directional bias mathematically cancels out (a team that scores +5 and a team that scores -5 will naturally balance the game total).

### 2. Updated Report Generator
We updated `run_confidence_report.py` and the CSV export logic to use the new `max` variables, preventing crashes and ensuring the new metrics are printed to the console and saved to the CSV files.

## The Results

The math fix had an immediate and massive impact on the report. 

**Before the fix (Today's Report):**
- `[HIGH]` Confidence Games: 4
- `[AVOID]` Games: 28

**After the fix (Today's Report):**
- `[HIGH]` Confidence Games: **1**
- `[AVOID]` Games: **50**

The engine is now fiercely filtering out the trash. Games where even *one* team is highly volatile are immediately being dumped into the `[LOW]` and `[AVOID]` buckets, meaning you will spend significantly less time auditing toxic games in the dashboard!
