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

t_wins = {1:0, 2:0, 3:0, 4:0}
t_tot = {1:0, 2:0, 3:0, 4:0}

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
        
        l = p.get('league', '').lower()
        if 'women' in l or 'woman' in l or 'ladies' in l or l.endswith(' w'): continue
        
        if h_vol < 14.8 and a_vol < 14.8:
            tier = 1
        elif h_vol <= 16.6 and a_vol <= 16.6:
            tier = 2
        elif h_vol > 16.6 and a_vol > 16.6:
            tier = 4
        else:
            tier = 3
            
        actual_total = act_h + act_a
        t_tot[tier] += 1
        if actual_total >= model_total:
            t_wins[tier] += 1

print('MENS FLAT FLOOR AUDIT (April 12 to 18):')
print(f'%-35s | %-6s | %-15s' % ('Stability Tier', 'Games', 'Win Rate (Actual >= Model)'))
print('-' * 70)

names = {
    1: 'Tier 1: BOTH Green (< 14.8)',
    2: 'Tier 2: BOTH Colored (<= 16.6)',
    3: 'Tier 3: ONE Unstable',
    4: 'Tier 4: BOTH Unstable (> 16.6)'
}

for i in range(1, 5):
    w = t_wins[i]
    t = t_tot[i]
    if t == 0: continue
    pct = (w / t) * 100
    print(f'{names[i]:<35} | {t:<6} | {w}/{t} ({pct:.1f}%)')
