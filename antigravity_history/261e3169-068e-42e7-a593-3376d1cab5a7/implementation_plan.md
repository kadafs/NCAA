# Fix: 145.5 Fallback Odds — NCAA Team Name Mismatch

## Problem

The render odds API returns game keys in `"school name nickname vs school name nickname"` format (e.g. `"clemson tigers vs florida state seminoles"`). The scoreboard gives short names like `"Clemson"` and `"Florida St."`.

`extract_total_for_matchup` cleans both and does a **substring check**:
- `clean_team_name("Florida St.")` → `"floridast"`
- `clean_team_name("florida state seminoles")` → `"floridastseminoles"`

`"floridast"` is **not** a substring of `"floridastseminoles"` → **no match → 145.5 fallback**.

Teams like Florida/Ole Miss work only because `"floridagators"` contains `"florida"` as a substring — a coincidence, not reliable matching.

## Fix

**One-file change: `utils/odds_provider.py` — `extract_total_for_matchup`**

In the Render API (dict) branch, before testing a key with `is_match()`, also test a **nickname-stripped** version of the key. The stripping strategy:

For a key like `"clemson tigers vs florida state seminoles"`:
1. Split on `" vs "` → `["clemson tigers", "florida state seminoles"]`
2. For each half, try dropping the **last word** (usually the nickname) → `["clemson", "florida state"]`
3. Run `is_match()` on both the original key **and** the stripped key

This is robust because NCAA team names in the odds API always follow `"<school> <nickname>"` format.

### [MODIFY] [odds_provider.py](file:///c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/utils/odds_provider.py)

In `extract_total_for_matchup`, replace the Render API dict branch (lines ~110–114):

```diff
-    # 1. Centralized Render API format (Dict: { "team a vs team b": total })
-    if isinstance(odds_data, dict) and "sport_events" not in odds_data:
-        for key, val in odds_data.items():
-            if is_match(key):
-                return val
-        return None
+    # 1. Centralized Render API format (Dict: { "team a vs team b": total })
+    if isinstance(odds_data, dict) and "sport_events" not in odds_data:
+        for key, val in odds_data.items():
+            # First: try matching the raw key
+            if is_match(key):
+                return val
+            # Second: try stripping the last word (nickname) from each half
+            # e.g. "clemson tigers vs florida state seminoles"
+            #   -> "clemson vs florida state" -> easier to match short names
+            if " vs " in key:
+                halves = key.split(" vs ", 1)
+                stripped = " vs ".join(
+                    " ".join(h.split()[:-1]) if len(h.split()) > 1 else h
+                    for h in halves
+                )
+                if stripped != key and is_match(stripped):
+                    return val
+        return None
```

## Why this is safe

- Only executed for the Render (dict) branch — no impact on Sportradar or Odds API paths.
- Only strips the **last word** from each team half; won't corrupt names like `"ole miss"` (already short) because stripping gives `"ole"` → if the original matched it would have returned already, so the stripped attempt is just an additional fallback.
- No aliases changed, no breaking changes elsewhere.

## Verification Plan

### Automated test (run directly in terminal)

```powershell
cd c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api

# Test 1: Confirm previously failing names now resolve
python -c "
from utils.odds_provider import get_odds, extract_total_for_matchup
data = get_odds('ncaa', provider='render')
tests = [
  ('Clemson',        'Florida St.'),
  ('Virginia Tech',  'Wake Forest'),
  (\"St. John's\",    'Creighton'),
  ('Chattanooga',    'The Citadel'),
  ('Louisiana',      'Texas State'),
  ('App State',      'Georgia Southern'),
  ('Mississippi St.','South Carolina'),
  ('North Carolina', 'Syracuse'),
]
success, fail = 0, 0
for away, home in tests:
    r = extract_total_for_matchup(data, away, home)
    status = 'OK' if r and r != 145.5 else 'FAIL'
    if status == 'OK': success += 1
    else: fail += 1
    print(f'[{status}] {away} @ {home}: {r}')
print(f'\nResult: {success}/{success+fail} resolved')
"

# Test 2: Re-run the conf model and check how many games still get 145.5
python ncaa/predict_d1_conf.py --mode safe 2>&1 | Select-String "market_total|Market:"
```

### Expected outcome
- Most matchups that previously showed 145.5 should now show real lines (e.g. 148.5, 151.0, etc.)
- Some games genuinely have no odds available (very early or low-profile games) and will legitimately stay at 145.5 — those are acceptable
