---
description: Daily NBL1 prediction workflow for Safe and Full modes
---

## Context

NBL1 season runs **March to September** (Australian winter). Games are played across 5 conferences (Central, East, North, South, West) typically on **Saturday and Sunday AEST** (Fri/Sat US Eastern time).

The API-Basketball free tier allows **100 requests/day**. A full 5-conference stats refresh uses ~55 requests, so you can do 1 full refresh per day comfortably.

---

## Step 1 — Refresh Data

Fetch the latest stats and today's schedule. Do this once per day, in the morning before games tip off.

```bash
python nbl1/fetch_nbl1_stats.py
python nbl1/fetch_nbl1_schedule.py
```

Or use the integrated refresh flag:

```bash
python run_universal.py --league nbl1 --refresh
```

> **Note:** If the season hasn't started yet (before Mar 29, 2025), the schedule fetch will return 0 games for today's date — that's expected.

---

## Step 2 — Run Safe Mode

```bash
python run_universal.py --league nbl1 --mode safe
```

With trace to see the math:
```bash
python run_universal.py --league nbl1 --mode safe --trace
```

Safe Mode gives you: **Phase 1 only** — base total, pace impact, HCA, regression.
Clean, conservative predictions tied directly to team efficiency differentials.

---

## Step 3 — Run Full Mode

```bash
python run_universal.py --league nbl1 --mode full
```

With trace:
```bash
python run_universal.py --league nbl1 --mode full --trace
```

Full Mode adds the **Phase 2 Sharp Layer** on top of Safe Mode numbers:
- Elite offense boost
- Blowout volatility correction
- Form momentum (NBL1-only)
- Venue pace split
- Close game foul bonus
- Fatigue penalties (if B2B data is available)

---

## Step 4 — Compare & Decide

Run both and compare the edge direction and magnitude:

```bash
python run_universal.py --league nbl1 --mode safe  --trace > nbl1_safe.txt
python run_universal.py --league nbl1 --mode full  --trace > nbl1_full.txt
```

Decision guide:
- If **both modes agree on direction** (both UNDER or both OVER) → high confidence
- If **Full Mode narrows the edge** (e.g. Safe -14, Full -11) → sharp signals reduce conviction, size down
- If **Full Mode widens the edge** → sharp signals confirm, consider sizing up
- If modes **disagree on direction** → pass

---

## Step 5 — Targeting Specific Conferences / Dates

To fetch a single conference (saves API requests):
```bash
python nbl1/fetch_nbl1_stats.py --conf Central
python nbl1/fetch_nbl1_stats.py --conf North
```

To run predictions for a specific past date (backtesting):
```bash
python run_universal.py --league nbl1 --mode safe --date 2024-06-15
python run_universal.py --league nbl1 --mode full --date 2024-06-15
```

To fetch schedule for a specific date:
```bash
python nbl1/fetch_nbl1_schedule.py --date 2025-04-05 --season 2025
```

---

## Season Timing Reference

| Date | Event |
|---|---|
| March 29, 2025 | 2025 NBL1 season opens |
| March–May | Early season — lower model confidence, heavier regression |
| June–July | Mid-season — model most accurate (full sample) |
| August | Finals — smaller field, higher variance |
| September | Championship |

> **Tip:** Trust the model more from game 8+ onward (~late April). Early-season stats are small-sample and the 0.93 regression factor dampens extreme predictions.
