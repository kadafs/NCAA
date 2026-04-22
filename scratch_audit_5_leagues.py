import json
import os
import glob
from collections import defaultdict

DATA_DIR = 'data/basketball'
TRACKING_EPOCH = '2026-03-25'

TARGET_LEAGUES = [
    'SPAIN - PRIMERA FEB',
    'SWITZERLAND - SB LEAGUE',
    'RUSSIA - VTB UNITED LEAGUE',
    'GERMANY - PRO B',
    'GERMANY - BBL'
]

valid_leagues = set()
with open(f'{DATA_DIR}/league_leaderboard.json', 'r', encoding='utf-8') as f:
    for entry in json.load(f).get('leaderboard', []):
        adv_g = (entry.get('adv') or {}).get('graded_totals', 0)
        srs_g = (entry.get('srs') or {}).get('graded_totals', 0)
        if max(adv_g, srs_g) >= 5 and entry.get('league_id'):
            valid_leagues.add(str(entry.get('league_id')))

all_files = sorted(glob.glob(f'{DATA_DIR}/universal_predictions_*.json'))
files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]

# stats[league][tier] = {'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0}
stats = defaultdict(lambda: defaultdict(lambda: {'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0}))

for p_file in files:
    data = json.load(open(p_file, 'r', encoding='utf-8'))
    for p in data.get('predictions', []):
        if str(p.get('league_id')) not in valid_leagues: continue
        
        l_name = f"{p.get('country', '')} - {p.get('league', '')}".upper().replace('\u2014', '-')
        
        # Match target leagues loosely
        is_target = False
        matched_name = ""
        for t in TARGET_LEAGUES:
            if t.split(' - ')[1] in l_name:
                is_target = True
                matched_name = t
                break
                
        if not is_target: continue
        
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
        stats[matched_name][tier]['total'] += 1
        if actual_total >= model_total:
            stats[matched_name][tier]['wins_flat'] += 1
        if actual_total >= (model_total - 5):
            stats[matched_name][tier]['wins_5'] += 1
        if actual_total >= (model_total - 10):
            stats[matched_name][tier]['wins_10'] += 1

tier_names = {
    1: 'Tier 1 (Green)',
    2: 'Tier 2 (Colored)',
    3: 'Tier 3 (One Unstable)',
    4: 'Tier 4 (Both Unstable)'
}

for league in TARGET_LEAGUES:
    print(f'\n=== {league} ===')
    print(f'{"Tier":<22} | {"Games":>5} | {"Flat Floor":>15} | {"-5 Points":>15} | {"-10 Points":>15}')
    print('-' * 80)
    
    league_data = stats.get(league, {})
    if not league_data:
        print("No graded games found for this league in the tracked period.")
        continue
        
    for t in range(1, 5):
        d = league_data.get(t, {'total': 0, 'wins_flat': 0, 'wins_5': 0, 'wins_10': 0})
        tot = d['total']
        if tot == 0:
            print(f'{tier_names[t]:<22} | {tot:>5} | {"-":>15} | {"-":>15} | {"-":>15}')
            continue
            
        pct_flat = (d['wins_flat'] / tot) * 100
        pct_5 = (d['wins_5'] / tot) * 100
        pct_10 = (d['wins_10'] / tot) * 100
        
        flat_str = f"{d['wins_flat']}/{tot} ({pct_flat:.0f}%)"
        str_5 = f"{d['wins_5']}/{tot} ({pct_5:.0f}%)"
        str_10 = f"{d['wins_10']}/{tot} ({pct_10:.0f}%)"
        
        print(f'{tier_names[t]:<22} | {tot:>5} | {flat_str:>15} | {str_5:>15} | {str_10:>15}')
