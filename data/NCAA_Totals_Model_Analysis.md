
# NCAA Totals Model Performance Review & Professional Assessment

## 1. High-Level Performance Snapshot

**Volume**
- ~30 total plays
- Strong bias toward **Unders** (~70% of selections)

**Observed Results**
- Unders underperformed relative to Overs
- Losses clustered around:
  - Blowouts
  - Unexpected pace spikes
  - Late-game foul inflation / garbage time
  - Small model edges (≤3 points)

This indicates *structural issues*, not random variance.

---

## 2. Where the Model Was Correct

### Strong Edge Plays (≥6 pts)

These generally performed well:

- **Kent State vs Toledo**
  - Market: 161.5  
  - Model: 153.4 (–8.1 edge)  
  - Final: 147 ✅  
- **Buffalo vs Miami OH**
  - Market: 165.5  
  - Model: 155.9 (–9.6 edge)  
  - Final: 144 ✅  
- **Murray State vs UIC**
  - Model edge: –4.5  
  - Final: 155 (Under 158.5) ✅  

**Key Insight:**  
When the model edge exceeded ~6 points, directional accuracy was strong.

---

## 3. Failure Patterns

### A. Small-Edge Unders (Major Leak)

Examples:
- Dayton vs St. Bonaventure: –0.12  
- Illinois State vs Southern Illinois: –0.58  
- Loyola Chicago vs La Salle: –1.03  
- Ball State vs Bowling Green: –1.64  

**Reality Check**
- NCAA totals standard deviation ≈ 9–11 points
- A 1–2 point edge is statistically insignificant

**Rule:**  
> Any edge under **±4.0 = PASS**

---

### B. Blowout Volatility

Examples:
- UConn 92–60 Xavier  
- UCLA 98–66 Rutgers  
- Belmont 103–90 Drake  
- Boise State 91–87 Nevada  

**Issue**
- One team exceeded baseline scoring
- Garbage time inflated totals
- Bench units increased pace

**Fix**
Add **Blowout Volatility Modifier**:
- Spread ≥9  
  - Unders: –3 to –5 confidence penalty  
  - Overs: +2 to +3 boost  

---

### C. Elite Offense Misclassification

Misses included:
- Davidson vs Saint Louis  
- Tennessee vs Ole Miss  
- Texas vs South Carolina  

**Problem**
- Offensive efficiency is more repeatable than defense
- Model overweights defensive suppression

**Adjustment**
- If both teams rank top-40 offensively:
  - Reduce defensive dampeners by 50%
  - Especially in neutral or tournament games

---

## 4. Overtime & Endgame Inflation

Observed in:
- Close spreads (≤3)
- Aggressive fouling
- Extended final minutes

**Rule to Add**
- Spread ≤3 and Total <150  
  → Add +3 Over bias or downgrade Under

---

## 5. Quantitative Pattern Summary

| Scenario | Outcome |
|--------|--------|
| Model edge ≥6 | Profitable |
| Model edge ≤3 | Losing |
| Unders in blowouts | Very poor |
| Overs with strong edge | Strong |
| Slow pace + close game | Best Unders |
| Fast pace + fouls | Overs dominate |

---

## 6. Professional Recommendations

### 1. Tighten Entry Criteria
- Play only when:
  - Edge ≥5.0  
  - Or ≥4.0 with strong situational support

### 2. Rebalance Portfolio
- Current: ~70% Unders  
- Target:
  - 55–60% Unders
  - 40–45% Overs

### 3. Add Missing Modifiers
Mandatory additions:
1. Blowout volatility
2. Late-game foul inflation
3. Offense > defense weighting

### 4. Separate Variance vs Structural Misses
- Track:
  - Good read / bad variance
  - Bad structure / bad bet

---

## 7. Final Assessment

The model is **above average** but currently:
- Too conservative
- Too Under-heavy
- Too tolerant of small edges
- Overconfident in pace control

With refinements, this can evolve into a **scalable, professional-grade NCAA totals model**.

**Next steps (optional):**
- Upgrade to *PPG+PED Hybrid Totals v2*
- Implement confidence-tier staking
