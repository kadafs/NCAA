"""
Check how many games in the May 5 confidence report hit the default MAE of 12.0.
Also check leaderboard graded_totals distribution.
"""
import json
import csv

# Check CSV for default values
print("=== CSV Analysis: avg_mae distribution ===")
rows = list(csv.DictReader(open('data/confidence_reports/confidence_2026-05-05.csv', encoding='utf-8')))
hitting_default = [r for r in rows if float(r['avg_mae']) == 12.0]
print(f"Total game rows: {len(rows)}")
print(f"Rows with avg_mae == 12.0 (default fallback): {len(hitting_default)}")
for r in hitting_default[:10]:
    print(f"  {r['away_team']:25} @ {r['home_team']:25}  league:{r['league']}")

print()

# Check leaderboard for graded_totals distribution
d = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))
lb = d.get('leaderboard', [])

from collections import Counter
buckets = Counter()
for e in lb:
    g = e.get('graded_totals', 0)
    if g == 0:     buckets['0'] += 1
    elif g <= 3:   buckets['1-3'] += 1
    elif g <= 10:  buckets['4-10'] += 1
    elif g <= 20:  buckets['11-20'] += 1
    else:          buckets['21+'] += 1

print("=== Leaderboard: graded_totals distribution ===")
for k in ['0', '1-3', '4-10', '11-20', '21+']:
    print(f"  {k:>5} graded games:  {buckets[k]} teams")

print()

# Show teams with graded_totals <= 3 (very sparse MAE data)
sparse = [e for e in lb if 0 < e.get('graded_totals', 0) <= 3]
print(f"Teams with 1-3 graded games (sparse MAE): {len(sparse)}")
for e in sparse[:15]:
    name = e.get('name', '').encode('ascii', 'ignore').decode('ascii')
    print(f"  {name:30} graded:{e['graded_totals']:2}  MAE:{e.get('mae')}  league:{e.get('league_id')}")
