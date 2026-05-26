# UI Improvements Walkthrough

Two major UI updates successfully implemented and pushed to GitHub.

## 1. Basketball Status Abbreviations
All basketball game statuses have been standardized to a 2-character abbreviation format in `Football-Dashboard`.

- **PP**: Postponed
- **CN**: Canceled
- **SU**: Suspended
- **AB**: Abandoned
- **IN**: Interrupted
- **TL**: Technical Loss
- **WO**: Walkover
- **FF**: Forfeit
- **AW**: Awarded
- **HT**: Halftime
- **Q1-Q4**: Quarters
- **OT**: Overtime
- **FT**: Finished

## 2. Night Shift (Dark Mode)
A global dark mode system has been added to the Football Dashboard with automatic and manual controls.

### Features
- **Auto-Schedule**: Automatically turns ON at **19:00 (7 PM)** and OFF at **06:00 (6 AM)** local time.
- **Manual Override**: A toggle button next to the **Compact** mode switch allows users to manually switch themes.
- **Persistence**: User preference is saved in `localStorage`.
- **Theme Sync**: The app polls every 60 seconds to ensure the theme matches the current time (unless overridden manually).
- **Logo Optimization**: Swaps between `logo.png` (light) and `darklogo.png` (dark) with `mix-blend-mode: screen` to ensure perfect rendering against dark backgrounds.

## Files Modified
- [BasketballRow.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/BasketballRow.jsx): Expanded `formatStatus` mapping.
- [App.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/App.jsx): Implemented Night Shift state and auto-logic.
- [Header.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/Header.jsx): Logo swapping logic.
- [index.css](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/index.css): Dark theme CSS variables and component overrides.

### Verification
- [X] Basketball statuses are ≤ 2 characters.
- [X] Dark mode correctly overrides light mode variables.
- [X] Night Shift button shows `AUTO` label when follow schedule.
- [X] Logo renders clearly on both themes.
