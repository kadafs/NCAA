# Task Plan: Dual-Model (SRS + Advanced) Execution

- [x] Draft implementation plan for dual-model execution.
- [x] Discuss approach with the user and get approval.
- [x] Refactor `run_basketball_daily.py` to load both SRS and Advanced stats simultaneously.
- [x] Update `run_basketball_daily.py` main game loop
    - [x] Integrate sequential dual-runs for `[SRS]` and `[ADVANCED]` where available.
- [x] Ensure terminal and JSON outputs clearly distinguish between the two runs (SRS vs Advanced).
- [x] Verify functionality with a test run.
- [x] Refine Dual Model Accuracy
    - [x] Implement Four Factors efficiency math for ADV model
    - [x] Update `grade_basketball.py` for per-model grading
    - [x] Update `aggregate_basketball_stats.py` for per-model leaderboards
    - [x] Update `audit_basketball.py` with model-specific filters
    - [x] Design and Implement Frontend Dual Accuracy Pills
    - [x] Synchronize Data and Push to GitHub
        - [x] Run `npm run build` & `sync-data.js`
        - [x] Commit and Push all changes to master branch
        - [x] Troubleshoot missing advanced predictions for Greece A2, Sweden Basketligan, Serbia First League
            - [x] Identify root causes for missed triggers
            - [x] Update `league_slug_map.json` for Sweden and Serbia
            - [x] Implement team name mapping for Greece (Psychikou)
            - [x] Regenerate advanced metrics and verify predictions
        - [x] Cleanup temporary session scripts
- [x] Final Walkthrough & Verification

# Task Plan: Daily Proballers Scraper Optimization
- [x] Draft implementation plan for `--daily` scraper optimization
- [x] Discuss approach with user and get approval
- [x] Implement `get_daily_urls(date_str)` in `scrape_proballers.py`
- [x] Optimize `scrape_proballers.py` with `--daily` flag
    - [x] Integrate with `run_basketball_daily.py` for fixture data
    - [x] Implement dual-lookup for Proballers URLs (configs vs legacy)
    - [x] Filter out USA and excluded leagues
- [x] Fix League Stats name collision (Kosovo/Venezuela)
    - [x] Update `aggregate_basketball_stats.py` with unique keys
    - [x] Update frontend `App.jsx` lookup logic
- [x] Resolve Git merge conflicts and push to master branchg
- [x] Final Walkthrough & Verification

- [x] Fix mapping for provided Proballers leagues
    - [x] Identify API-Basketball IDs for Bosnia, Portugal, Spain (LEB), Switzerland (NLB)
    - [x] Update `league_slug_map.json` with new slugs
    - [x] Verify Advanced metrics generation

# UI Improvement: Advanced Model Priority with SRS Flag
- [x] Research duplication cause in `App.jsx` and `LeagueGroup.jsx`
- [x] Create implementation plan for ADV priority with SRS flag
- [x] Update `App.jsx` to group games by fixture
- [x] Refactor `BasketballRow.jsx` to show SRS as a flag in the ADV row
- [x] Refine SRS flag styling (centered extension)
- [x] Implement ADV priority in League Header (hide SRS)
- [x] Global FT cleanup (Check `status === 'FT'`, `status === 'Finished'`, or `isGraded`)
- [x] Final Centering for SRS flag (explicitly set flex styles)
- [x] Verify visual fix in all leagues (BSN, CIBACOPA, CBA)

# UI Refinement: Mute XPTS Colors & Card Style
- [x] Draft implementation plan to mute XPTS orange saturation
- [x] Discuss approach with user and get approval (XPTS Mute)
- [x] Update CSS variables and classes in `index.css` (XPTS Mute)
- [x] Draft implementation plan for card-style match rows
- [x] Discuss approach with user and get approval (Card Style)
- [x] Update `.match-row` styling in `index.css`
- [x] Verify visual improvement in browser
- [x] Commit and push changes
- [x] Final UI Alignment: Tabular Numbers & Flex-Widths (CANCELLED - Rolled back to d4d538f)
    - [x] Update `index.css` with fixed-width utilities and `tabular-nums` (Discarded)
    - [x] Refactor `BasketballRow.jsx` to usage-based utility classes (Discarded)
    - [x] Refactor `MatchRow.jsx` to usage-based utility classes (Discarded)
    - [x] Align `LeagueGroup.jsx` header with matching flex containers (Discarded)
- [x] UI Refinement: Adaptive Grid (CANCELLED - Rolled back to d4d538f)
    - [x] Restructure `index.css` with layout rules for Desktop, Tablet, and Mobile (Discarded)
    - [x] Apply `.match-info`, `.match-tip` wrappers to `BasketballRow.jsx` (Discarded)
    - [x] Apply `.match-info`, `.match-tip` wrappers to `MatchRow.jsx` (Discarded)
    - [x] Sync `.league-header` columns in `LeagueGroup.jsx` (Discarded)
