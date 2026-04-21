import json
import os
import glob
from collections import defaultdict

DATA_DIR = 'data/basketball'
TRACKING_EPOCH = '2026-03-25'

valid_leagues = set()
with open(f'{DATA_DIR}/league_leaderboard.json', 'r', encoding='utf-8') as f:
    for entry in json.load(f).get('leaderboard', []):
        adv_g = (entry.get('adv') or {}).get('graded_totals', 0)
        srs_g = (entry.get('srs') or {}).get('graded_totals', 0)
        if max(adv_g, srs_g) >= 10 and entry.get('league_id'):
            valid_leagues.add(str(entry.get('league_id')))

all_files = sorted(glob.glob(f'{DATA_DIR}/universal_predictions_*.json'))
files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]

# Buckets with 5-point bands for more granularity
buckets = defaultdict(lambda: {'wins': 0, 'total': 0, 'over_margins': [], 'under_margins': []})

for p_file in files:
    data = json.load(open(p_file, 'r', encoding='utf-8'))
    for p in data.get('predictions', []):
        if str(p.get('league_id')) not in valid_leagues: continue
        
        act_h = p.get('actual_home_score')
        act_a = p.get('actual_away_score')
        model_total = p.get('model_total')
        if act_h is None or act_a is None or not model_total: continue
        
        h_vol = p.get('home_team_volatility')
        a_vol = p.get('away_team_volatility')
        if h_vol is None or a_vol is None: continue
        if h_vol >= 14.8 or a_vol >= 14.8: continue  # Tier 1 only
        
        l = p.get('league', '').lower()
        if 'women' in l or 'woman' in l or 'ladies' in l or l.endswith(' w'): continue
        
        bucket_low = int(model_total // 5) * 5
        bucket_key = f'{bucket_low}-{bucket_low + 4}'
        
        actual_total = act_h + act_a
        delta = actual_total - model_total
        buckets[bucket_key]['total'] += 1
        if actual_total >= model_total:
            buckets[bucket_key]['wins'] += 1
            buckets[bucket_key]['over_margins'].append(delta)
        else:
            buckets[bucket_key]['under_margins'].append(delta)

print('MEN\'S TIER 1 - FLAT FLOOR WIN RATE BY MODEL TOTAL RANGE (5-pt bands, full season)')
print(f'{"Range":<12} | {"Games":>5} | {"Win Rate":>14} | {"Avg Over":>9} | {"Avg Under":>10} | Verdict')
print('-' * 80)

for key in sorted(buckets.keys(), key=lambda x: int(x.split('-')[0])):
    b = buckets[key]
    t = b['total']
    w = b['wins']
    if t < 3: continue
    pct = (w / t) * 100
    avg_over = sum(b['over_margins']) / len(b['over_margins']) if b['over_margins'] else 0
    avg_under = sum(b['under_margins']) / len(b['under_margins']) if b['under_margins'] else 0
    
    if pct >= 60:
        verdict = '?? SWEET SPOT'
    elif pct >= 52.4:
        verdict = '?? PROFITABLE'
    else:
        verdict = '?? AVOID'
    
    print(f'{key:<12} | {t:>5} | {w}/{t} ({pct:.1f}%)    | {avg_over:>+8.1f} | {avg_under:>+9.1f} | {verdict}')
