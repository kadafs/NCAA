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

# Structure: stats[tier][league] = {'wins': 0, 'total': 0}
stats = {1: defaultdict(lambda: {'wins': 0, 'total': 0}),
         2: defaultdict(lambda: {'wins': 0, 'total': 0}),
         3: defaultdict(lambda: {'wins': 0, 'total': 0}),
         4: defaultdict(lambda: {'wins': 0, 'total': 0})}

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
        
        if h_vol < 14.8 and a_vol < 14.8:
            tier = 1
        elif h_vol <= 16.6 and a_vol <= 16.6:
            tier = 2
        elif h_vol > 16.6 and a_vol > 16.6:
            tier = 4
        else:
            tier = 3
            
        actual_total = act_h + act_a
        stats[tier][l_name]['total'] += 1
        
        # The key change: -5 point buffer
        if actual_total >= (model_total - 5):
            stats[tier][l_name]['wins'] += 1

tier_names = {
    1: 'TIER 1 (BOTH GREEN)',
    2: 'TIER 2 (BOTH COLORED)',
    3: 'TIER 3 (ONE UNSTABLE)',
    4: 'TIER 4 (BOTH UNSTABLE)'
}

for t in range(1, 5):
    print(f'\n=== {tier_names[t]} - LEAGUES AT -5 POINTS (>= 60% Win Rate) ===')
    print(f'{"League":<35} | {"Games":>5} | {"Win Rate":>14}')
    print('-' * 60)
    
    # Filter for minimum 4 games to avoid extreme noise
    filtered = {k: v for k, v in stats[t].items() if v['total'] >= 4}
    sorted_leagues = sorted(filtered.items(), key=lambda x: (x[1]['wins'] / x[1]['total'], x[1]['total']), reverse=True)
    
    found_good = False
    for l_name, b in sorted_leagues:
        pct = (b['wins'] / b['total']) * 100
        if pct >= 60.0:  
            print(f'{l_name[:35]:<35} | {b["total"]:>5} | {b["wins"]}/{b["total"]} ({pct:.1f}%)')
            found_good = True
            
    if not found_good:
        print("No leagues with >= 4 games hit the 60% threshold in this tier.")
