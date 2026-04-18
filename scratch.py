import json
import os
import re

DATES = ['2026-04-17', '2026-04-18']

valid_leagues = set()
with open('data/basketball/league_leaderboard.json', 'r', encoding='utf-8') as f:
    for entry in json.load(f).get('leaderboard', []):
        adv_g = entry.get('adv', {}).get('graded_totals', 0) if entry.get('adv') else 0
        srs_g = entry.get('srs', {}).get('graded_totals', 0) if entry.get('srs') else 0
        if max(adv_g, srs_g) >= 10 and entry.get('league_id'):
            valid_leagues.add(str(entry.get('league_id')))

print('\nMEN\'S TIER 1 GAMES (April 17 & 18):')
print('%-25s | %-35s | %-6s | %-6s | %-7s | %-6s' % ('League', 'Matchup', 'Model', 'Actual', 'Result', 'Margin'))
print('-' * 95)

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
        if 'women' in l or 'woman' in l or 'ladies' in l or re.search(r' w$', l): continue
        
        actual_total = act_h + act_a
        win = actual_total >= (model_total - 10)
        res_str = 'WIN' if win else 'LOSS'
        margin = actual_total - model_total
        
        matchup = f"{p.get('home_team')} vs {p.get('away_team')}"
        print(f"{p.get('league')[:23]:<25} | {matchup[:33]:<35} | {model_total:>6.1f} | {actual_total:>6} | {res_str:<7} | {margin:>+6.1f}")
