"""
Final verification for audit fixes #6 (batter hand) and #7 (speed tier).
Tests correctness of logic, not specific hardcoded API values.
Run from project root: python mlb/cache/verify_audit_6_7.py
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

import statsapi  # import first to avoid any re-init issues

results = []

# --- Test 1: Import chain ---
try:
    from fetch_lineups import get_batter_hand, get_pitcher_hand
    from live_state import get_runner_speed_tier, _ELITE_RUNNERS, _SLUGGISH_RUNNERS
    from monte_carlo_f5 import run_monte_carlo_f5
    results.append(('OK', 'Import chain - no circular dependency'))
except Exception as e:
    results.append(('FAIL', f'Import error: {e}'))
    print('\n'.join(f'  [{s}] {m}' for s, m in results)); sys.exit(1)

# --- Test 2: get_batter_hand returns only valid values ---
test_ids = [665862, 682829, 677951, 641355]
for pid in test_ids:
    result = get_batter_hand(pid)
    ok = result in ('L', 'R')
    results.append(('OK' if ok else 'FAIL',
                    f'get_batter_hand({pid}) returned valid value: {result!r}'))

# --- Test 3: get_batter_hand matches direct API response ---
# Fetch directly then compare — no cached intermediate values
for pid in [665862, 677951]:
    raw = statsapi.get('people', {'personIds': pid})
    api_code = raw['people'][0].get('batSide', {}).get('code', '?')
    # Switch hitters -> 'R' (no platoon penalty)
    expected = api_code if api_code in ('L', 'R') else 'R'
    got = get_batter_hand(pid)
    ok = (got == expected)
    name = raw['people'][0]['fullName']
    results.append(('OK' if ok else 'FAIL',
                    f'{name} ({pid}): API batSide={api_code!r} -> expected={expected!r} got={got!r}'))

# --- Test 4: Speed tiers ---
elite_ids = [677951, 682829, 665862]  # all in _ELITE_RUNNERS
for pid in elite_ids:
    in_set = pid in _ELITE_RUNNERS
    tier = get_runner_speed_tier(pid)
    ok = (in_set and tier == 2)
    results.append(('OK' if ok else 'FAIL',
                    f'Speed tier {pid}: in_elite_set={in_set}, tier={tier} (expected 2)'))

tier_vogelbach = get_runner_speed_tier(607043)
results.append(('OK' if tier_vogelbach == 0 else 'FAIL',
                f'Vogelbach (607043): tier={tier_vogelbach} (expected 0)'))

# --- Test 5: Delegation live_cache -> fetch_lineups ---
from live_cache import _get_batter_hand as cache_hand
for pid in [665862, 677951]:
    r1 = cache_hand(pid)
    r2 = get_batter_hand(pid)
    ok = (r1 == r2)
    results.append(('OK' if ok else 'FAIL',
                    f'Delegation pid={pid}: cache={r1!r} fetch_lineups={r2!r} match={ok}'))

# --- Summary ---
print('=' * 60)
print('Audit Fix Verification: Issues #6 and #7')
print('=' * 60)
all_pass = True
for status, msg in results:
    print(f'  [{status}] {msg}')
    if status == 'FAIL':
        all_pass = False

print()
print(f'All checks passed: {all_pass}')
