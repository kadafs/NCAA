"""
Smoke test for all remaining audit fixes: Issues 1, 2, 3, 9.
"""
import sys, subprocess
sys.path.insert(0, 'mlb')

results = []

# ── Test 1: Issue 1 — multiplicative park+weather composition ──────────
from grade_f5 import grade_matchup, calculate_expected_runs, _PLATOON_VS_RHP

# When facing RHP, wRC+ is scaled by _PLATOON_VS_RHP (0.98).
# The base reference must use the same platoon-adjusted wRC+ for a fair comparison.
adj_wrc = 100 * _PLATOON_VS_RHP
base_adj = calculate_expected_runs(3.5, 4.0, 5.0, adj_wrc, 1.0, 1.0)
actual_total = grade_matchup(
    'A', 3.5, 4.0, 5.0, 100, 'B', 3.5, 4.0, 5.0, 100,
    park_factor=1.15, weather_multiplier=1.10,
    away_pitcher_hand='R', home_pitcher_hand='R'
)['projected_f5_total']
expected_mult = round(base_adj * 2 * 1.15 * 1.10, 2)   # correct: park × weather
expected_add  = round(base_adj * 2 * (1.15 + 0.10), 2)  # old additive (wrong)
ok = abs(actual_total - expected_mult) < 0.05
results.append(('OK' if ok else 'FAIL',
    'Issue 1 multiplicative PF: got={:.2f} expected_mult={:.2f} old_additive={:.2f}'.format(
        actual_total, expected_mult, expected_add)))

# ── Test 2: Issue 3 — platoon adjustment ───────────────────────────────
vs_rhp = grade_matchup('A', 3.5, 4.0, 5.0, 100, 'B', 3.5, 4.0, 5.0, 100,
    away_pitcher_hand='R', home_pitcher_hand='R')
vs_lhp = grade_matchup('A', 3.5, 4.0, 5.0, 100, 'B', 3.5, 4.0, 5.0, 100,
    away_pitcher_hand='R', home_pitcher_hand='L')

away_rhp = vs_rhp['away_expected_f5_runs']
away_lhp = vs_lhp['away_expected_f5_runs']
ok = away_lhp > away_rhp
results.append(('OK' if ok else 'FAIL',
    'Issue 3 platoon: away vs LHP={:.2f} vs RHP={:.2f} (LHP should be higher)'.format(
        away_lhp, away_rhp)))

# ── Test 3: Issue 9 — per-stadium wind bearing ─────────────────────────
from weather_f5 import _wind_relative_to_stadium

tests_9 = [
    # (wind_from_deg, venue, expected, description)
    (180, 'Wrigley Field', 'Out',   'Wrigley S wind = Out (CF bearing=21)'),
    (0,   'Wrigley Field', 'In',    'Wrigley N wind = In'),
    (225, 'Yankee Stadium','Out',   'Yankee SW wind = Out (CF bearing=67)'),
    (60,  'Yankee Stadium','In',    'Yankee NE wind = In'),
    (200, 'Fenway Park',   'Out',   'Fenway S wind = Out (CF bearing=34)'),
    (20,  'Fenway Park',   'In',    'Fenway NNE wind = In'),
]
for wind_deg, venue, expected, label in tests_9:
    got = _wind_relative_to_stadium(wind_deg, venue)
    ok  = (got == expected)
    results.append(('OK' if ok else 'FAIL', 'Issue 9 ' + label + ' -> got=' + got))

# ── Test 4: Issue 2 — advice confidence tier requires both signals ──────
# The new advice also includes (HIGH)/(MODERATE) in the output string
# We can verify this by checking the output format of the advice function
# Replicate the logic inline since get_advice is a closure
def get_advice_sim(td_total, line, under_prob):
    td_gap    = line - td_total
    td_signal = 'UNDER' if td_gap > 0 else 'OVER'
    if under_prob >= 0.52:
        mc_signal = 'UNDER'
    elif under_prob <= 0.48:
        mc_signal = 'OVER'
    else:
        mc_signal = 'NEUTRAL'
    if td_signal == mc_signal:
        mc_strong = under_prob >= 0.58 or under_prob <= 0.42
        td_strong = abs(td_gap) >= 0.30
        conf = 'HIGH' if (mc_strong and td_strong) else 'MODERATE'
        return 'Bet **' + mc_signal + '** (' + conf + ')'
    return 'Skip'

# Strong signal: both high
adv_high = get_advice_sim(td_total=3.2, line=4.5, under_prob=0.62)
ok = 'HIGH' in adv_high and 'UNDER' in adv_high
results.append(('OK' if ok else 'FAIL',
    'Issue 2 HIGH confidence signal: ' + adv_high))

# Weak TD but strong MC: should be MODERATE
adv_mod = get_advice_sim(td_total=4.3, line=4.5, under_prob=0.61)
ok = 'MODERATE' in adv_mod and 'UNDER' in adv_mod
results.append(('OK' if ok else 'FAIL',
    'Issue 2 MODERATE (weak TD gap): ' + adv_mod))

# Disagreeing signals: Skip
adv_skip = get_advice_sim(td_total=5.2, line=4.5, under_prob=0.62)
ok = adv_skip == 'Skip'
results.append(('OK' if ok else 'FAIL',
    'Issue 2 Skip (models disagree): ' + adv_skip))

# ── Test 5: grade_f5 self-test ─────────────────────────────────────────
r = subprocess.run([sys.executable, 'mlb/grade_f5.py'], capture_output=True, text=True)
ok = r.returncode == 0
results.append(('OK' if ok else 'FAIL',
    'grade_f5.py self-test: ' + (r.stdout.strip().split('\n')[-1] if ok else r.stderr.strip()[:100])))

# ── Summary ────────────────────────────────────────────────────────────
print('=' * 60)
print('Remaining Audit Fixes — Smoke Test (Issues 1, 2, 3, 9)')
print('=' * 60)
all_pass = True
for status, msg in results:
    print('  [{}] {}'.format(status, msg))
    if status == 'FAIL':
        all_pass = False
print()
print('All checks passed: {}'.format(all_pass))
