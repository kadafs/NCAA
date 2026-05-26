# Daily SDI Report Tool

This plan outlines the creation of a new standalone tool `run_daily_sdi_report.py` that will allow you to instantly see the SDI ratings for all matches occurring on a specific date, without having to search teams individually.

## Proposed Changes

### [NEW] `run_daily_sdi_report.py`
We will create a new script that will:
1. Accept an optional `--date` parameter (e.g., `--date 2026-05-05`). If no date is provided, it will automatically default to today's date.
2. Load the daily fixtures from `data/basketball/universal_predictions_{DATE}.json`.
3. Load the SDI index from `data/basketball/team_sdi.json`.
4. Utilize the robust string-matching logic we built earlier (including the `" W"` suffix rules for Women's leagues and the first-word fallback) to perfectly map the daily teams to their SDI records.
5. Print out a beautifully formatted terminal report that highlights:
   * **Highest Risk Teams Playing Today**: Any individual team playing today with an SDI > 55% (High Dependency).
   * **Most Volatile Matches**: Matches where *both* teams have a high SDI, meaning extreme variance.
   * **Most Stable Matches**: Matches where *both* teams are incredibly balanced (Lowest combined SDI), meaning they are safe flat-floor volume plays.

## Verification Plan
1. Write the script.
2. Run `python run_daily_sdi_report.py` (which defaults to today, 2026-05-05).
3. Verify that the output cleanly displays the matches sorted by SDI, successfully finding matches from active leagues.
4. Verify that the Women's teams (like NBL1 Women) are correctly matched and not bleeding into Men's statistics.

## Open Questions
- Do you want to restrict this report to only output matches from specific stability Tiers (e.g., only show Tier 1/2 matches), or should it list all matches on the slate regardless of tier? (I will default to showing all matches, but flagging their Tiers for context).
