"""
General nullification pass for any awarded match (0-20 or 20-0) 
that slipped through before the guard was added.
"""
import json, glob

AWARDED_SCORE_PATTERNS = [(0, 20), (20, 0)]

total_nullified = 0

for f in sorted(glob.glob('data/basketball/universal_predictions_*.json')):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
    except Exception as e:
        print(f"Error reading {f}: {e}")
        continue

    predictions = data.get('predictions', [])
    changed = 0

    for p in predictions:
        # Already nullified
        if p.get('awarded_match'):
            continue

        h = p.get('actual_home_score')
        a = p.get('actual_away_score')

        if h is None or a is None:
            continue

        try:
            h, a = int(h), int(a)
        except (TypeError, ValueError):
            continue

        if (h, a) in AWARDED_SCORE_PATTERNS:
            league = p.get('league', '?')
            home = p.get('home_team', '?')
            away = p.get('away_team', '?')
            print(f"  NULLIFYING [{f[-15:-5]}] [{league}] {home} {h} - {a} {away}")
            p['actual_home_score'] = None
            p['actual_away_score'] = None
            p['actual_result']     = None
            p['total_delta']       = None
            p['signed_delta']      = None
            p['total_rpe']         = None
            p['accuracy_tier']     = None
            p['awarded_match']     = True
            changed += 1

    if changed:
        data['predictions'] = predictions
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False)
        print(f"  Saved {f} ({changed} record(s) nullified)")
        total_nullified += changed

print(f"\nDone. Total awarded matches nullified: {total_nullified}")
