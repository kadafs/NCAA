# Two UI Improvements: Status Abbreviations + Night Shift Toggle

Two changes across the basketball and football frontends:
1. All basketball game statuses abbreviated to ≤ 2 characters
2. A "Night Shift" dark-mode toggle in both frontends

---

## Proposed Changes

### Basketball Frontend — Status Abbreviations

The `formatStatus()` function in `BasketballRow.jsx` already handles NS, HT, Q1–Q4, OT, but doesn't cover statuses like "Game Postponed", "Cancelled", "Suspended", etc. — these fall through to their raw string.

#### [MODIFY] [BasketballRow.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/BasketballRow.jsx)

Expand `formatStatus()` to cover all known API-basketball statuses with 2-char abbreviations:

| Raw Status | Abbreviation |
|---|---|
| `NOT STARTED` / `SCHEDULED` | `NS` |
| `GAME POSTPONED` / `POSTPONED` | `PP` |
| `CANCELLED` / `CANCELED` | `CN` |
| `SUSPENDED` | `SU` |
| `ABANDONED` | `AB` |
| `INTERRUPTED` | `IN` |
| `TECHNICAL LOSS` | `TL` |
| `WALKOVER` | `WO` |
| `HALFTIME` | `HT` |
| `QUARTER 1` | `Q1` |
| `QUARTER 2` | `Q2` |
| `QUARTER 3` | `Q3` |
| `QUARTER 4` | `Q4` |
| `OVERTIME` | `OT` |
| `FINISHED` / `FT` / `GAME FINISHED` | `FT` |

Also update the `FINISHED_STATUSES` set to catch more variants.

---

### Night Shift Toggle — Both Frontends

#### Football Dashboard (Vite/React — `football-dashboard/`)

**Strategy:** Add a CSS dark-mode variable block triggered by a `data-theme="dark"` attribute on `<body>`. Toggle is controlled by App-level state, persisted in `localStorage`, and a `🌙` button placed in the `Header` component.

##### [MODIFY] [index.css](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/index.css)
Add a `[data-theme="dark"]` override block redefining all `--` CSS variables to dark equivalents (deep navy background, lighter text, darkened cards/rows).

##### [MODIFY] [App.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/App.jsx)
- Add `nightShift` state initialized from `localStorage`, defaulting to `false`
- On mount / on change: set `document.body.dataset.theme = nightShift ? 'dark' : 'light'`
- Pass `nightShift` and `toggleNightShift` down to `Header`

##### [MODIFY] [Header.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/Header.jsx)
Add a `🌙/☀️` toggle button to the `header-right` section. Accepts `nightShift` + `toggleNightShift` props.

---

#### Basketball Frontend (Next.js — `frontend/`)

**Strategy:** Same CSS variable approach. Since Next.js already uses Tailwind-like class/variable system, we add dark overrides via a `data-theme="dark"` on `<html>` in a client layout wrapper. The toggle is in the existing `Header.tsx`.

##### [MODIFY] [Header.tsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/frontend/src/components/Header.tsx)
- Add `nightShift` state initialized from `localStorage` 
- On mount / on change: set `document.documentElement.dataset.theme`
- Add `🌙/☀️` toggle button in the nav bar right section

##### [MODIFY] [globals.css or tailwind config](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/frontend/src)
Check where CSS variables are defined and add `[data-theme="dark"]` block. (Need to identify the CSS file used — likely `app/globals.css`)

---

## Verification Plan

### Manual Verification

1. **Status Abbreviations (Basketball):**
   - Run the football-dashboard locally: `cd football-dashboard && npm run dev`
   - Switch to "Basketball" tab in the header
   - Look for any game row that shows a non-abbreviated status (e.g. full "Game Postponed" text in time column)
   - Confirm it now shows as `PP`
   - Confirm existing statuses NS, HT, Q1–Q4, OT, FT still display correctly

2. **Night Shift Toggle — Football Dashboard:**
   - With dev server running, click the `🌙` button in the header
   - Confirm the entire page switches to a dark theme
   - Refresh the page — confirm dark mode persists (localStorage)
   - Click `☀️` to toggle back — confirm it returns to light mode

3. **Night Shift Toggle — Basketball Frontend:**
   - Run: `cd frontend && npm run dev`
   - Click the `🌙` button in the top nav bar
   - Confirm the page switches to dark mode
   - Refresh — confirm it persists
