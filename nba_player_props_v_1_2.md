# Masterplan: NBA Player Props v1.2 (Advanced Redistribution)

## 1. Objective
To move beyond simple linear scaling and implement a dynamic redistribution model that accounts for lineup changes, defensive mismatches, and recent performance trends.

---

## 2. The "Usage Vacuum" Logic (Primary Upgrade)
When a high-usage player is OUT, their stats are redistributed based on "Usage Proximity."

### A. The Hierarchy
- **Primary Beneficiary**: The player moving into the starting lineup (minutes spike).
- **Secondary Beneficiary**: The remaining 1st/2nd scoring options (usage rate spike).

### B. Math: The Redistribution Factor (RF)
If a player averaging 30% usage is OUT:
- **RF (New Starter)**: `(Projected Minutes / Avg Minutes) * 1.15` (15% efficiency bonus for fresh legs).
- **RF (Remaining Stars)**: `+12% to Points and Assists` baseline.

---

## 3. The "Defensive Funnel" Modifier
We will integrate "Points Allowed per Position" (PApP) to identify mismatches.

| Defense Profile | Prop Impact |
| :--- | :--- |
| **Elite Rim Protection** | -10% Points for Centers/Slashers |
| **Weak Wing Defense** | +15% Points/Assists for SF/SG |
| **High TOV Creator** | -10% Assists for PGs (Trap-heavy) |

---

## 4. The 3-Step Forecast (Refined)

### Step 1: Seasonal Baseline (Weighted Form)
`Final Baseline = (Season Avg * 0.4) + (Last 5 Games Avg * 0.6)`
- *Rationale*: NBA roles change rapidly. Recent form is the best indicator of current role.

### Step 2: Game Environment Scaling
`Scaled Prop = Final Baseline * (Projected Team Total / Season Avg PPG)`
- *Note*: If the game total is 240+ (fast pace), high-volume shooters get a "Volume Bonus."

### Step 3: Cleanup & Governance
- **Minute Caps**: Ensure no player is projected for more than 40 minutes (unless OT is likely).
- **Injury Overlays**: Final check against the "Usage Vacuum" table.

---

## 5. Persistence & Transparency
The `NBATotalsEngine` (from v1.2) will be extended to include a `PropEngine` function that outputs:
- **`prop_projection`**: The final number.
- **`logic_trace`**: e.g., "Bumped +15% due to Embiid OUT; Reduced -10% due to Kawhi defensive matchup."

---

## 6. Implementation Roadmap
1. **`nba/v1_2/prop_engine.py`**: A new class for handling redistributed logic.
2. **Update `fetch_nba_stats.py`**: Fetch opponent "Points Allowed per Position" (PApP).
3. **Update `predict_nba_full.py`**: Switch to the v1.2 Prop Engine for the primary dashboard display.
