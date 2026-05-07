import json
import sys

BANDS = [
    ("< 2",    lambda s: s < 2),
    ("2 - 5",  lambda s: 2 <= s < 5),
    ("5 - 8",  lambda s: 5 <= s < 8),
    ("8 - 11", lambda s: 8 <= s < 11),
    ("11-15",  lambda s: 11 <= s < 15),
    ("15-20",  lambda s: 15 <= s < 20),
    ("> 20",   lambda s: s >= 20)
]

def make_bucket():
    return {'total': 0, 'over_flat': 0, 'over_5': 0, 'over_10': 0, 'actual': [], 'model': []}

data = {label: make_bucket() for label, _ in BANDS}
skipped = 0

with open('data/basketball/universal_predictions_2026-05-06.json', 'r', encoding='utf-8') as f:
    preds = json.load(f)

for p in preds.get('predictions', []):
    act_h      = p.get('actual_home_score')
    act_a      = p.get('actual_away_score')
    model_total = p.get('model_total')
    xpts_h     = p.get('xpts_h')
    xpts_a     = p.get('xpts_a')

    if act_h is None or act_a is None or not model_total:
        skipped += 1; continue
    if xpts_h is None or xpts_a is None:
        skipped += 1; continue

    spread = abs(float(xpts_h) - float(xpts_a))
    actual = float(act_h) + float(act_a)
    model  = float(model_total)

    for label, test in BANDS:
        if test(spread):
            bucket = data[label]
            bucket['total']    += 1
            bucket['actual'].append(actual)
            bucket['model'].append(model)
            if actual >= model:          bucket['over_flat'] += 1
            if actual >= (model - 5):   bucket['over_5']    += 1
            if actual >= (model - 10):  bucket['over_10']   += 1
            break

print("=" * 92)
print("  SPREAD AUDIT — TODAY (2026-05-06)")
print("=" * 92)
print(f"  {'Spread':>8}  {'Games':>6}  {'OverFlat':>9}  {'Over-5':>7}  {'Over-10':>8}  {'AvgActual':>10}  {'AvgModel':>9}  {'AvgDelta':>9}")
print("  " + "-"*80)

for label, _ in BANDS:
    b = data[label]
    n = b['total']
    if n == 0:
        print(f"  {label:>8}  {'0':>6}")
        continue
    avg_act   = sum(b['actual']) / n
    avg_mod   = sum(b['model'])  / n
    avg_delta = avg_act - avg_mod
    of_pct  = b['over_flat'] / n * 100
    o5_pct  = b['over_5']    / n * 100
    o10_pct = b['over_10']   / n * 100
    print(f"  {label:>8}  {n:>6}  {b['over_flat']:>4} ({of_pct:5.1f}%)  "
          f"{b['over_5']:>3} ({o5_pct:5.1f}%)  "
          f"{b['over_10']:>4} ({o10_pct:5.1f}%)  "
          f"{avg_act:>10.1f}  {avg_mod:>9.1f}  {avg_delta:>+9.1f}")

total_games = sum(b['total'] for b in data.values())
print(f"\n  Total graded today: {total_games}  |  Skipped: {skipped}")
print("=" * 92)
