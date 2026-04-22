import json
import os
import glob

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

wins_5 = 0
wins_10 = 0
total = 0

for p_file in files:
    data = json.load(open(p_file, 'r', encoding='utf-8'))
    for p in data.get('predictions', []):
        if str(p.get('league_id')) not in valid_leagues: continue
        
        l_name = f"{p.get('country', '')} - {p.get('league', '')}".upper()
        if 'GREECE - A2' not in l_name: continue
        
        act_h = p.get('actual_home_score')
        act_a = p.get('actual_away_score')
        model_total = p.get('model_total')
        if act_h is None or act_a is None or not model_total: continue
        
        h_vol = p.get('home_team_volatility')
        a_vol = p.get('away_team_volatility')
        if h_vol is None or a_vol is None: continue
        if not (h_vol > 16.6 and a_vol > 16.6): continue # Tier 4 only
        
        actual_total = act_h + act_a
        total += 1
        if actual_total >= (model_total - 5): wins_5 += 1
        if actual_total >= (model_total - 10): wins_10 += 1

print(f'GREECE - A2 (Tier 4): Games: {total}, Wins (-5): {wins_5}, Wins (-10): {wins_10}')
