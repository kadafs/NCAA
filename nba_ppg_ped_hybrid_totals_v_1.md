# Masterplan: NBA PPG+PED Hybrid Totals Model v1.2

## 1. Objective
To create a high-discipline, deterministic forecasting engine for NBA game totals that balances raw scoring historicals (PPG) with advanced efficiency metrics (PED) and pro-specific situational context (Load Management).

---

## 2. Philosophy: "The Pro Gravity Theory"
Unlike the NCAA, where variance is high and talent is unbalanced, the NBA is a high-efficiency system.
1. **Regulated Efficiency**: NBA teams are elite; a "bad" NBA defense is still more efficient than most NCAA programs.
2. **The 3P Variance**: 3-point volume is the primary driver of O/U variance in the modern NBA.
3. **Situational Fatigue**: The schedule (Back-to-Backs) is as impactful as the stats.

---

## 3. Operating Modes
- **SAFE MODE (Statistical Baseline)**: Uses only the 12 numerical columns. No injury context.
- **FULL MODE (Contextual Reality)**: Applies the "Star Leverage" layer (Injuries, B2B, Rest).

---

## 4. Input Sheet Architecture (NBA Mapping)
| Column | Metric | Source |
| :--- | :--- | :--- |
| `team_ppg` | Season Points Per Game | Season Stats |
| `opp_ppg` | Opponent Season PPG | Season Stats |
| `pace_delta` | Team Pace vs League Avg (100.0) | `nba_api` |
| `eff_delta` | Off/Def Eff vs League Avg (115.0) | `nba_api` |
| `3p_volume` | 3PA per 100 possessions | `nba_api` |
| `fatigue_factor` | B2B indicator (0 or -2.0) | Schedule |

---

## 5. Core Model Logic (The 6-Step Forecast)

### Step 1: Raw Baseline
`(Team A PPG + Team B PPG) / 2 * 2` (Standard Combined PPG).

### Step 2: Pace Acceleration (The 100.0 Pivot)
- Calculate `Matchup Pace = (Team A Pace + Team B Pace) / 2`.
- `Pace Adjustment = (Matchup Pace - 100.0) * 1.5`.
- *Rationale*: NBA totals are hyper-sensitive to transitions.

### Step 3: Efficiency Calibration (The 115.0 Pivot)
- Calculate `Matchup Efficiency = (OffA + DefB + OffB + DefA) / 4`.
- `Efficiency Adj = (Matchup Efficiency - 115.0) * 0.8`.

### Step 4: The "3P Variance" Modifier
- If combined 3PA (3-Point Attempts) > 75 per game: `+1.5 points`.
- If combined 3PA < 65 per game: `-2.0 points`.

### Step 5: Schedule Fatigue (B2B)
- If one team is on a Back-to-Back: `-2.0 total points` (Defense usually lags, but shooting tired usually drops the total).
- If BOTH teams are on B2B: `-4.0 total points`.

### Step 6: Star Leverage (Full Mode Only)
- **Superstar OUT**: `-4.5 points` (e.g., Embiid, Giannis).
- **Secondary Star OUT**: `-2.0 points`.
- **Governance Rule**: Contextual notes cannot flip an "A-Grade PASS" to a "PLAY."

---

## 6. Output Classification (The Hedge Strategy)
- **MODE A (Elite Edge)**: Model deviates from Market by `> 7.5 points`.
- **MODE B (Standard Edge)**: Model deviates by `> 4.5 points`.
- **PASS**: Deviation `< 4.5 points`.

---

## 7. Performance Attribution
Every prediction must save a `reasoning_trace` to `data/nba_v1_2_logs.json` to allow for coefficient recalibration every 30 days.
