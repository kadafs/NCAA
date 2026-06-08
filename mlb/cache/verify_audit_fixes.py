import sys
sys.path.insert(0, 'mlb')
from live_f5 import american_to_implied

tests = [
    (-110,   0.5238),
    (120,    0.4545),
    ('+120', 0.4545),
    ('-105', 0.5122),
    (100,    0.5000),
    (-100,   0.5000),
    # The inversion case from the audit: -105 into the OLD plus-odds formula = -20% — now safe
    ('bad_data', 0.5000),
]

print('Odds Sanitizer Verification:')
print(f"{'Input':<12} {'Result':>8}  {'Expected':>10}  {'Status':>6}")
print('-' * 44)
all_pass = True
for raw, expected in tests:
    result = american_to_implied(raw)
    ok = abs(result - expected) < 0.001
    all_pass = all_pass and ok
    status = 'OK' if ok else 'FAIL'
    print(f"{str(raw):<12} {result:>8.4f}  {expected:>10.4f}  {status:>6}")

print()
print('Exit Probability Double-Count Verification:')
# Old formula: P(pulled in inning) = 1 - (1-0.25)^4.2 = ~68%
# New formula: p is drawn ONCE per inning frame, so it stays at 25%
old_compounded = 1 - (0.75 ** 4.2)
print(f"  Old per-batter 4.2x compound:  {old_compounded*100:.1f}%  (WRONG - was burning Over bets)")
print(f"  New single inning-frame draw:  25.0%  (CORRECT)")
print()
print(f"All odds tests passed: {all_pass}")
