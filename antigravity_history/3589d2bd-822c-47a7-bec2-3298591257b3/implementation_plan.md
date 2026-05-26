# Incorporating Empirical Hit Rate Into the Confidence Engine

## Goal
The Confidence Report currently scores games based on model *inputs* (Volatility, MAE, Bias, Spread). These metrics predict how *predictable* a game should be in theory. But the user observed that manually checking the Custom Audit hit rates produced better betting results.

The fix: add **Empirical Flat Floor Hit Rate** as a 5th scoring dimension, forcing a game to prove its predictability in actual historical results — not just on paper.

---

## How It Works

For each upcoming game, the engine will look up how often **each team** has historically produced a final score at or above the model's projected total. We apply the same **Worst Maximum** philosophy from the Volatility fix: a game must clear the bar for **both** teams independently. The **lower** (worst) hit rate of the pair is used to score the game.

**Example:**
- Rimini flat floor hit rate: 70%
- Pesaro flat floor hit rate: 33%
- Engine uses: **33%** → Low score, game gets penalized

---

## Proposed Changes

### Step 1: `aggregate_basketball_stats.py` — Compute Hit Rates

#### [MODIFY] `aggregate_basketball_stats.py`
For each `(team_name, league_id)` entry being aggregated, compute:
- `flat_floor_hits`: count of graded games where `actual_total >= model_total`
- `flat_floor_total`: total graded games for the team

These are stored into `basketball_leaderboard.json` under each team entry as `flat_floor_hits` and `flat_floor_total`, giving us a raw hit rate of `flat_floor_hits / flat_floor_total`.

> [!NOTE]
> Requires `python aggregate_basketball_stats.py --regrade` to populate all historical entries.

---

### Step 2: `run_confidence_report.py` — Load and Pass Hit Rate

#### [MODIFY] `get_team_stats()` function
Update the function signature to also return `flat_floor_hit_rate` from the leaderboard entry:
```python
# Returns (mae, bias, graded, flat_floor_hit_rate, source)
```

Update the call sites so the new value is passed into `compute_confidence()`:
```python
game = {
    ...existing keys...,
    "hit_rate_a": hit_rate_a,   # Pesaro's flat floor %
    "hit_rate_b": hit_rate_b,   # Rimini's flat floor %
}
```

---

### Step 3: `core/confidence_score.py` — Score the Hit Rate

#### [MODIFY] `core/confidence_score.py`

**New scoring function:**
```python
def score_hit_rate(min_hit_rate: float) -> int:
    """
    Scores the game based on the WORST flat floor hit rate of the two teams.
    Uses Flat Floor (actual >= model_total) — the strictest and most relevant
    metric for totals betting.

    Thresholds (flat floor hit rate %):
        >= 80% → 27  (very reliable — consistent floor hitters)
        >= 65% → 18
        >= 50% →  9
         < 50% →  0  (team undershoots more often than not — automatic fail)
    """
    if min_hit_rate >= 0.80: return 27
    elif min_hit_rate >= 0.65: return 18
    elif min_hit_rate >= 0.50: return 9
    else: return 0
```

**Sample size guard:**
If either team has fewer than 5 graded games, treat as neutral (`9 points`) to avoid penalizing new teams unfairly.

**Updated normalization:**
The max raw score changes from 75 → **85**.
```python
confidence_score = round((raw_score / 85) * 100, 1)
```

**Updated score breakdown:**
| Component | Max Points | Weight | Role |
|---|---|---|---|
| **Empirical Hit Rate (Min)** | **27** | **32%** | **PRIMARY — did both teams prove it?** |
| Volatility (Max) | 20 | 24% | Secondary — is the environment stable? |
| MAE (Max) | 15 | 18% | Supporting — is the model accurate? |
| Bias (Avg) | 15 | 18% | Supporting — is the model directionally correct? |
| Spread | 8 | 9% | Tie-breaker |
| **Total** | **85** | **100%** | |

---

## Verification Plan

1. Run `python aggregate_basketball_stats.py --regrade` to populate `flat_floor_hits` and `flat_floor_total`.
2. Run `python run_confidence_report.py --no_playoffs` and verify:
   - Pesaro vs Rimini drops further (Pesaro's 33% flat floor hit rate should push it from 64.0 to a much lower score).
   - Saint Quentin U21 vs Nancy U21 holds up (both teams' hit rates are reasonable within their own league).
3. Check that games with small sample sizes (`< 5 games`) don't get unfairly penalized.

## Open Questions
> [!IMPORTANT]
> **Which buffer level should we use for the hit rate?**
> - **Flat Floor** (actual ≥ model): Strictest. Directly tells you if the team hits the stated total. Recommended.
> - **-5 pts** (actual ≥ model - 5): More lenient. Might inflate scores.
> 
> My recommendation: **Flat Floor** only. We are betting on the model total, not a discounted line.

> [!NOTE]
> **Weight of the new dimension**
> Hit Rate carries 27 points (32% of the final score), making it the single most important individual dimension. Volatility drops from 27pts to 20pts and becomes secondary. This reflects the user's empirical finding that historical floor performance is a more reliable predictor than model-based stability metrics alone.
