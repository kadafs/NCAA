import json
import os

DATES = ['2026-04-12', '2026-04-13', '2026-04-14', '2026-04-15', '2026-04-16', '2026-04-17', '2026-04-18']

valid_leagues = set()
with open('data/basketball/league_leaderboard.json', 'r', encoding='utf-8') as f:
    for entry in json.load(f).get('leaderboard', []):
        adv_g = entry.get('adv', {}).get('graded_totals', 0) if entry.get('adv') else 0
        srs_g = entry.get('srs', {}).get('graded_totals', 0) if entry.get('srs') else 0
        if max(adv_g, srs_g) >= 10 and entry.get('league_id'):
            valid_leagues.add(str(entry.get('league_id')))

t1_wins = 0
t1_total = 0

for d in DATES:
    p_file = f'data/basketball/universal_predictions_{d}.json'
    if not os.path.exists(p_file): continue
    
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
        if h_vol >= 14.8 or a_vol >= 14.8: continue
        
        l = p.get('league', '').lower()
        if 'women' in l or 'woman' in l or 'ladies' in l or l.endswith(' w'): continue
        
        actual_total = act_h + act_a
        t1_total += 1
        if actual_total >= model_total:
            t1_wins += 1

print('MENS TIER 1 FLAT FLOOR (Exact Model Total):')
print(f'{t1_wins} Wins / {t1_total} Games')
pct = (t1_wins / t1_total) * 100 if t1_total > 0 else 0
print(f'Win Rate: {pct:.1f}%')
