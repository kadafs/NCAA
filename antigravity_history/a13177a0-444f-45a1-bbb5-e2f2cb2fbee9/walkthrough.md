# Walkthrough: UI Refinements & Rollback

> [!IMPORTANT]
> This session concluded with a **final rollback to commit `d4d538f`**. Three UI Refinement layout attempts—"Unified Grid System", "Flex-Based Tabular Alignment", and "Adaptive Grid"—were cancelled as per the user's instructions.

# Basketball Dual-Model & Efficiency Update Walkthrough

Successfully implemented a robust dual-model system for basketball predictions, providing a clear distinction between the **SRS (Standard)** and **ADVANCED (Efficiency)** models.

## ⚙️ Core Backend Changes

### 1. Four Factors Efficiency Math
Updated `generate_advanced_metrics.py` to use a genuine ADVANCED model based on basketball efficiency metrics:
- **True Shooting % (TS%)**
- **Turnover Rate (TOV%)**
- **Offensive Rebound % (ORB%)**
These metrics are calculated from box-score data and normalized to league averages, creating a model that is distinctly different from the point-differential-based SRS.

### 2. Model-Aware Grading & Aggregation
- **`grade_basketball.py`**: Modified to track wins, losses, and accuracy tiers separately for `[SRS]` and `[ADVANCED]` architectures.
- **`aggregate_basketball_stats.py`**: Refactored the leaderboard generation to store independent `srs` and `adv` stats objects for every league.
- **`audit_basketball.py`**: Added a new `--model` flag (`srs`, `adv`, `all`) to allow auditing each model's performance independently.

## 💻 Frontend Dashboard Enhancements

### 1. Dual Accuracy Pills
The league header now displays separate, model-labeled accuracy pills if the league has dual-model history:
- 🟦 **SRS Pill**: Shows SRS MAPE, bullseyes, and 1X2 record.
- 🟣 **ADV Pill**: Shows ADV MAPE, bullseyes, and 1X2 record.

### 2. Model-Aware MAPE Filtering
The MAPE filter in the control bar now checks the specific model's historical accuracy based on the tag of the prediction row (`SRS` or `ADVANCED`).

## ✅ Validation Results

- **Data Check**: Verified that today's predictions (March 23) correctly output two distinct records (SRS and ADV) per game with different point spreads.
- **Leaderboard Check**: Confirmed that leagues like ABA League and Superliga correctly show diverging MAPEs for SRS vs ADV (e.g., Superliga: SRS 12.8% vs ADV 3.1%).
- **Git Push**: All code, updated data, and frontend components have been pushed to the `master` branch on GitHub.

---

## 🚀 Daily Scraper Optimization
Implemented a highly efficient `--daily` flag for `scrape_proballers.py` to prevent unnecessary scraping of leagues that aren't playing.

### Functionality
1. **Dynamic Target Resolution**: When `python scrape_proballers.py --daily today` is run, the script reads `data/api_basketball_today_{date}.json` to identify exactly which leagues have games.
2. **Config Mapping**: It cross-references the active leagues against `configs/leagues/*.json` to locate only the valid `proballers_url`s.
3. **Optimized Extraction**: Instead of looping through all 40+ configured Proballers leagues (which takes roughly 15 minutes and risks Cloudflare shadowbans), it exclusively targets the 2-5 leagues active on that specific day.

> **Validation**: Tested against March 23rd fixtures. Initially, it only found 3 mapped leagues (because `configs/leagues/*.json` lacked the `proballers_url` for most older leagues). I have now implemented a **Dual-Lookup strategy** that falls back to the legacy mapping (`data/league_slug_map.json` + `proballers_schedule_links.txt`). To guarantee perfect parity with the frontend, the scraper now explicitly imports `run_basketball_daily`'s league filters. Testing reveals this perfectly extracted the **11** international active leagues for today while automatically disregarding irrelevant USA entities like NBA, NCAA, and the G-League.

> [!TIP]
> From tomorrow morning, after running `grade_basketball.py`, you will see the first set of results where the ADV model is using the new Four Factors math!
 
## League Stats Collision Fix
Identified and resolved a bug where leagues with the same name (e.g., "SUPERLIGA") were sharing statistics.
- **Root Cause**: `aggregate_basketball_stats.py` was grouping data solely by the league's name string.
- **Fix**: Implemented a **Unique ID Strategy**. Aggregation now uses `league_id` and composite display names (e.g., "KOSOVO — SUPERLIGA").
- **Frontend Parity**: Updated the React dashboard to look up MAPE scores via `league_id` instead of raw strings.
- **Result**: Every league now has independent, accurate performance tracking!

## [FIX] Missing Advanced Predictions for Greece, Sweden, Serbia
- **Greece A2**: Added team name override for `Psychikou` -> `Psyhiko Athens` in `run_basketball_daily.py`.
- **Sweden Basketligan**: Fixed ID collision in `league_slug_map.json` (sweden-basketligan 190 -> 93).
- **Serbia First League**: Added missing `serbia-kls` mapping to `league_slug_map.json`.
- **Verification**: Regenerated math matrices and confirmed `[ADVANCED]` model triggers in daily runner for all three leagues.

## [NEW] Extended League Mapping Fixes
Successfully mapped and verified the 4 remaining international leagues provided:
- **Bosnia Division I**: Mapped to ID **123** (Prvenstvo BiH).
- **Portugal Liga Profissional**: Mapped to ID **261** (Liga Betclic).
- **Spain LEB Gold**: Mapped to ID **95** (Primera FEB).
- **Spain LEB Silver**: Mapped to ID **96** (Segunda FEB).

> [!NOTE]
> **Switzerland NLB** was confirmed as **missing** from the API-Basketball master league list (scanned 427 leagues). No mapping was added to avoid data corruption.

### Verification of Core Metrics
Ran full regeneration and confirmed the following files are active and populated with advanced stats:
- `data/bball_stats_123_adv.json`
- `data/bball_stats_261_adv.json`
- `data/bball_stats_95_adv.json`
- `data/bball_stats_96_adv.json`

## CBA Game Deduplication & ADV Priority
- **Status**: Completed
- **Changes**: 
  - **Fixture Grouping**: Grouped basketball predictions by match (Home + Away + Time) in `App.jsx`.
  - **ADV Priority**: The **ADVANCED** [🟣 ADV] model is now automatically used as the primary row display.
  - **Refined SRS Flag**: Implemented a centered, pill-like **SRS Total** flag directly attached to the bottom of the main model total box.
  - **Header ADV Priority**: Updated `LeagueGroup.jsx` to hide SRS stats in the league header when ADVANCED stats are available, ensuring a cleaner "ADV-first" display.
  - **Finished Game Cleanup**: Hidden the ADV/SRS model badge in the status column once a game is finished (`FT`), focusing the view on the result.
  - **Single Match Center**: Expanding a row now shows a single set of tabs (H2H, Stats, Standings) using the high-priority ADV data.
  - **Consolidated Summary**: Updated the dashboard summary counts to reflect unique matches rather than individual model runs.

## 🎨 Product-Grade UI Refinement (Final)
Successfully transformed the flat match list into a modern, interactive card-based system with several UX-focused micro-optimizations:

### 1. Card-Style Rows
- **Card Base**: Every match row is now a distinct card with `10px` rounded corners, subtle shadows, and defined margins (`6px` vertical).
- **Stability**: Implemented a "reserved" transparent left-border to prevent layout jumps when hovering or expanding.
- **GPU Performance**: Added `will-change: transform` to ensure the elevation animation is buttery smooth.

### 2. Interaction Hierarchy
- **Hover Affordance**: Hovering over a card provides a light indigo tint and a subtle `-1px` lift, signaling clickability.
- **Active Focus**: Expanded cards act as the "star" of the UI, gaining a bold left-border accent (`var(--brand)`), a deeper shadow, and a subtle "focus-ring" outline.

### 3. Balanced Visual Contrast
- **Muted XPTS/xG**: Further reduced orange saturation (`#fff9f2` bg) to ensure the column doesn't compete with the primary TIP badge.
- **Tone-Down Secondary Text**: Lightened contrast for timestamps and labels (Slate 400) to clear visual clutter and improve scannability.

---
**Verification**: Confirmed all hover, focus, and transition states are active on both Football and Basketball dashboards. Pushed all final styling fixes to the `master` branch.
