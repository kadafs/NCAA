# Remove 1X2 Grading from Basketball Headers

Remove the "1X2: [W]W-[L]L ([rate]%)" grading summary from the basketball league headers in the dashboard, so that only the MAPE and games count are displayed.

## Proposed Changes

### Components Setup

#### [MODIFY] [LeagueGroup.jsx](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/football-dashboard/src/components/LeagueGroup.jsx)

Remove the conditional block inside `renderStats` that renders the 1X2 hit rate for basketball games.

```jsx
// Remove this block inside renderStats:
-                  {(mStats.outcome_w + mStats.outcome_l > 0) && (
-                    <span style={{ fontSize: 10, fontWeight: 600, color: color, opacity: 0.8, paddingLeft: 4, borderLeft: `1px solid ${border}` }}>
-                      1X2: {mStats.outcome_w}W-{mStats.outcome_l}L ({mStats.outcome_hit_rate}%)
-                    </span>
-                  )}
```

## Verification Plan

### Automated Tests
- None.

### Manual Verification
1.  Open the dashboard.
2.  Switch to the **Basketball** tab.
3.  Check the headers for each league (e.g., "POLAND — 1 LIGA").
4.  Confirm that the header only shows the model name and MAPE (e.g., "ADV MAPE 6.5% (9g)") and no longer displays the 1X2 grading breakdown.
