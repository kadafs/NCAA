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

league_stats = defaultdict(lambda: {'wins': 0, 'total': 0})

for p_file in files:
    data = json.load(open(p_file, 'r', encoding='utf-8'))
    for p in data.get('predictions', []):
        if str(p.get('league_id')) not in valid_leagues: continue
        
        l_name = f"{p.get('country', '')} - {p.get('league', '')}".upper()
        if 'WOMEN' in l_name or 'LADIES' in l_name or ' W' in l_name: continue
        
        act_h = p.get('actual_home_score')
        act_a = p.get('actual_away_score')
        model_total = p.get('model_total')
        
        if act_h is None or act_a is None or not model_total: continue
        
        h_vol = p.get('home_team_volatility')
        a_vol = p.get('away_team_volatility')
        
        if h_vol is None or a_vol is None: continue
        if h_vol >= 14.8 or a_vol >= 14.8: continue  # TIER 1 ONLY
            
        actual_total = act_h + act_a
        
        league_stats[l_name]['total'] += 1
        # The key change: -10 point buffer
        if actual_total >= (model_total - 10):
            league_stats[l_name]['wins'] += 1

# Filter leagues with at least 3 Tier 1 games to remove extreme noise
filtered_leagues = {k: v for k, v in league_stats.items() if v['total'] >= 3}

# Sort by win rate descending
sorted_leagues = sorted(filtered_leagues.items(), key=lambda x: (x[1]['wins'] / x[1]['total'], x[1]['total']), reverse=True)

print('MEN\'S TIER 1 - TEASER (-10) WIN RATE BY LEAGUE')
print(f'{"League":<35} | {"Games":>5} | {"Win Rate":>14}')
print('-' * 60)

for l_name, b in sorted_leagues:
    t = b['total']
    w = b['wins']
    pct = (w / t) * 100
    print(f'{l_name[:35]:<35} | {t:>5} | {w}/{t} ({pct:.1f}%)')
