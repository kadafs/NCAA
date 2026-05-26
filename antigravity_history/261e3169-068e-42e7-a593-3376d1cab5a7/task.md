# Fixing NCAA Odds Fallback & Player Props Sorting

## Goal
Resolve the issue where NCAA game odds default to 145.5 and improve the player props page sorting.

## Tasks
- [x] Enhance player props sorting (edge, projection, line, name, matchup)
- [x] Investigate root cause of 145.5 NCAA odds fallback
- [x] Implement nickname-stripping logic in `utils/odds_provider.py` to fix name matching
- [x] Add ESPN as a secondary odds source for small-conference coverage
- [x] Add missing team aliases for LIU, USC Upstate, and Southeastern Louisiana
- [x] Verify resolution for previously failing matchups
- [x] Push all code changes to GitHub
