import json
import os
import glob

DATA_DIR = 'data/basketball'
TRACKING_EPOCH = '2026-03-25'

TARGET_LEAGUES = [
    'ARGENTINA \u2014 LIGA A',
    'BRAZIL \u2014 NBB',
    'INDONESIA \u2014 IBL',
    'JAPAN \u2014 B LEAGUE'
]

valid_leagues = set()
with open(f'{DATA_DIR}/league_leaderboard.json', 'r', encoding='utf-8') as f:
    for entry in json.load(f).get('leaderboard', []):
        adv_g = (entry.get('adv') or {}).get('graded_totals', 0)
        srs_g = (entry.get('srs') or {}).get('graded_totals', 0)
        if max(adv_g, srs_g) >= 10 and entry.get('league_id'):
            valid_leagues.add(str(entry.get('league_id')))

all_files = sorted(glob.glob(f'{DATA_DIR}/universal_predictions_*.json'))
files = [f for f in all_files if os.path.basename(f).replace('universal_predictions_','').replace('.json','') >= TRACKING_EPOCH]

t_wins = {1:0, 2:0, 3:0, 4:0}
t_tot = {1:0, 2:0, 3:0, 4:0}

for p_file in files:
    data = json.load(open(p_file, 'r', encoding='utf-8'))
    for p in data.get('predictions', []):
        if str(p.get('league_id')) not in valid_leagues: continue
        
        l_name = f"{p.get('country', '')} \u2014 {p.get('league', '')}".upper()
        # Allow fuzzy match for the target leagues
        is_target = False
        for t_league in TARGET_LEAGUES:
            if t_league in l_name or t_league.replace('\u2014', '-').replace(' ', '') in l_name.replace(' ', '').replace('-', ''):
                is_target = True
                break
            # Also check if just 'LIGA A' and 'ARGENTINA' are both in it, etc
            parts = t_league.split(' \u2014 ')
            if len(parts) == 2 and parts[0] in l_name and parts[1] in l_name:
                is_target = True
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
        t_tot[tier] += 1
        if actual_total >= model_total:
            t_wins[tier] += 1

print('FLAT FLOOR AUDIT (Target Leagues Only):')
print(', '.join(TARGET_LEAGUES).replace('\u2014', '-'))
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
    if t == 0: 
        print(f'{names[i]:<35} | {t:<6} | N/A')
        continue
    pct = (w / t) * 100
    print(f'{names[i]:<35} | {t:<6} | {w}/{t} ({pct:.1f}%)')
