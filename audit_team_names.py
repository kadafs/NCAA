"""
audit_team_names.py
--------------------
Compares today's API fixture team names against the advanced stats matrices,
AFTER applying TEAM_NAME_OVERRIDES from run_basketball_daily.py.
Only reports teams that would genuinely fail to match in the daily pipeline.
"""
import json, os, sys, datetime
from difflib import SequenceMatcher

sys.stdout.reconfigure(encoding='utf-8')

# ── Load overrides from the daily runner ──────────────────────────────────────
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("daily", "run_basketball_daily.py")
    daily = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(daily)
    OVERRIDES = daily.TEAM_NAME_OVERRIDES
except Exception as e:
    print(f"[WARN] Could not load TEAM_NAME_OVERRIDES: {e}")
    OVERRIDES = {}

print(f"  Loaded {len(OVERRIDES)} overrides from run_basketball_daily.py")

# ── Load today's fixtures ─────────────────────────────────────────────────────
today_str = datetime.date.today().isoformat()
today_file = f"data/api_basketball_today_{today_str}.json"
if not os.path.exists(today_file):
    # fallback to most recent
    import glob
    files = sorted(glob.glob("data/api_basketball_today_*.json"))
    today_file = files[-1] if files else None

if not today_file or not os.path.exists(today_file):
    print("ERROR: No today fixture file found.")
    sys.exit(1)

today = json.load(open(today_file, encoding='utf-8'))
print(f"  Using fixture file: {today_file}\n")

# ── Audit ─────────────────────────────────────────────────────────────────────
mismatches = {}

for l in today['leagues_summary']:
    lid = l['league_id']
    adv_path = f'data/bball_stats_{lid}_adv.json'
    if not os.path.exists(adv_path):
        adv_path = f'data/bball_stats_{lid}_srs.json'
    if not os.path.exists(adv_path):
        continue

    matrix = json.load(open(adv_path, encoding='utf-8'))
    matrix_names = [t['team_name'] for t in matrix.get('teams', [])]
    if not matrix_names:
        continue

    for g in l['games']:
        for side in ['home', 'away']:
            raw_name = g.get(side, '')
            if not raw_name:
                continue

            # Step 0: Apply overrides (same as daily runner)
            api_name = OVERRIDES.get(raw_name, raw_name)
            api_lower = api_name.lower()

            # Step 1: Exact match
            if any(m == api_name or m.lower() == api_lower for m in matrix_names):
                continue
            # Step 2: Substring
            if any(m.lower() in api_lower or api_lower in m.lower() for m in matrix_names):
                continue
            # Step 3: difflib
            scores = [(SequenceMatcher(None, api_lower, m.lower()).ratio(), m) for m in matrix_names]
            best_score, best_match = max(scores)
            if best_score >= 0.85:
                continue

            key = (lid, l.get('league', f'League-{lid}'))
            if key not in mismatches:
                mismatches[key] = []
            # Avoid duplicate team reports per league
            if not any(x[0] == raw_name for x in mismatches[key]):
                mismatches[key].append((raw_name, api_name, round(best_score, 2), best_match))

# ── Report ────────────────────────────────────────────────────────────────────
print(f"{'='*70}")
print(f"  TEAM NAME MISMATCH AUDIT — {today_str}")
print(f"{'='*70}")

if not mismatches:
    print("\n  ✅  No mismatches found. All teams mapped correctly.\n")
else:
    total = 0
    for (lid, lname), items in sorted(mismatches.items()):
        print(f"\n  [{lid}] {lname}")
        for raw_name, resolved_name, score, closest in items:
            if raw_name != resolved_name:
                print(f"    API raw:    \"{raw_name}\" -> override: \"{resolved_name}\"  ← still no matrix match!")
            else:
                print(f"    API:        \"{raw_name}\"")
            print(f"    Matrix best: \"{closest}\"  (sim={score})")
            total += 1
    print(f"\n  ⚠️  Total unresolved mismatches: {total}")

print(f"{'='*70}\n")
