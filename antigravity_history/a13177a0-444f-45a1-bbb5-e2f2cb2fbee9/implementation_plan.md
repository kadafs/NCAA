# Adaptive Grid Implementation

Implement a 3-tier Adaptive Grid system to intelligently restructure match rows based on viewport size, preventing "squished" numbers on smaller screens while maintaining data density on desktop.

## Proposed Changes

### [CSS] index.css
- **Desktop (Base):**
  - Define `.match-row.basketball` and `.match-row.football` with full grid columns (e.g., `1.8fr 70px 110px 100px 90px`).
  - Assign specific grid columns to child classes (`.match-info`, `.match-tip`, `.match-prob`, etc.).
  - Apply `font-variant-numeric: tabular-nums` to ensure numeric stability.
- **Tablet (max-width: 1024px):**
  - Tighten grid columns.
  - Hide least priority columns (`.match-xpts` for basketball, `.match-play` for football).
- **Mobile (max-width: 768px):**
  - Switch from a single row to a 2-row (basketball) or 3-row (football) stacked card layout using `grid-template-rows` and specific `grid-column` / `grid-row` assignments.
  - Increase `.match-row` padding and refine font sizes for readability.

### [Components] BasketballRow.jsx & MatchRow.jsx
- Group "Time" and "Teams" inside `.match-info`.
- Assign specific usage-based utility classes to the columns: `.match-tip`, `.match-prob`, `.match-model` / `.match-xg`, `.match-xpts` / `.match-btts`, `.match-play`.
- Add `.basketball` or `.football` to the `.match-row` wrapper.

### [Header] LeagueGroup.jsx
- Update `.league-header` to match the exact same responsive grid structure as the rows.
- Ensure the header also collapses or hides columns on Tablet/Mobile in alignment with the data rows.

## Verification Plan
### Automated Tests
- Serve the application locally and use browser DevTools to simulate Desktop, Tablet (1024px), and Mobile (768px) viewports, verifying that the layout gracefully adapts to the specified structures.
