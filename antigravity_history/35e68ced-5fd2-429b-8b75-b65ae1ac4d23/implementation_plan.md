# Implementing Compact Dashboard Mode

The goal is to implement a "Compact Mode" for the football dashboard to improve usability on mobile and tablet devices. This involves adding a persistent toggle in the header, removing the desktop-only `min-width` constraint, and applying CSS-driven layout adjustments (stacked team names, hidden secondary columns like xG/xPTS).

## User Review Required

> [!IMPORTANT]
> - Compact mode is auto-detected once on first load for devices < 1024px.
> - User manual overrides are prioritized and persisted via `localStorage`.
> - Header alignment was corrected by removing `gap` from the `league-header` grid.

## Proposed Changes

### Frontend Components

#### [MODIFY] [App.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/App.jsx)
- Added `compactMode` state with `localStorage` persistence.
- Implemented single-run auto-detection for mobile/tablet (`window.innerWidth < 1024`).
- Added a first-time user hint toast for mobile users.
- Applied `.compact-mode` class to the root container.

#### [MODIFY] [Header.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/Header.jsx)
- Added a "⊟ Compact / ⊞ Full" toggle button.

#### [MODIFY] [LeagueGroup.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/LeagueGroup.jsx)
- Added structural classes (`football`, `basketball`, `match-xg`, `match-xpts`) for CSS targeting.
- Aligned padding to match row layout.

#### [MODIFY] [MatchRow.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/MatchRow.jsx)
- Added `football`, `teams`, `match-xg`, and `match-chevron` classes.
- Removed inline conditional rendering for compact mode.

#### [MODIFY] [BasketballRow.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/BasketballRow.jsx)
- Added `basketball`, `teams`, `match-xpts`, and `match-chevron` classes.
- Removed inline grid templates and conditional logic.

### Styling

#### [MODIFY] [index.css](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/index.css)
- Removed `min-width: 1200px` from `body`.
- Implemented `.compact-mode` CSS overrides (stacked layout, column hiding, density tuning).
- Fixed grid track alignment by removing `gap` from `league-header`.

## Verification Plan

### Automated Tests
- Run `npm run build` to ensure no breaks.

### Manual Verification
- Toggle "Compact/Full" in the header and verify layout shifts.
- Inspect grid alignment with DevTools.
- Verify persistence by reloading the page after toggling.
- Verify mobile auto-detect by clearing `localStorage` and resizing to < 1024px before first load.
