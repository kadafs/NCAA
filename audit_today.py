import json
import sys
import os
sys.path.append('.')
from core.confidence_score import compute_confidence

def get_team_stats(team_name, league_id, lb_entries):
    for entry in lb_entries:
        if str(entry.get('league_id')) == str(league_id) and entry.get('name', '').lower() == team_name.lower():
            return entry.get('mae', 15.0), entry.get('avg_signed_delta', 0.0), entry.get('graded_totals', 0)
    return 15.0, 0.0, 0

with open('data/basketball/basketball_leaderboard.json', encoding='utf-8') as f:
    lb = json.load(f).get('leaderboard', [])

with open('data/basketball/universal_predictions_2026-05-06.json', encoding='utf-8') as f:
    data = json.load(f)

tiers = {
    '[ELITE]   ': {'g':0, 'w':0, 'w5':0}, 
    '[HIGH]    ': {'g':0, 'w':0, 'w5':0}, 
    '[SOLID]   ': {'g':0, 'w':0, 'w5':0}, 
    '[MODERATE]': {'g':0, 'w':0, 'w5':0}, 
    '[LOW]     ': {'g':0, 'w':0, 'w5':0}, 
    '[AVOID]   ': {'g':0, 'w':0, 'w5':0}
}

for p in data.get('predictions', []):
    act_h = p.get('actual_home_score')
    act_a = p.get('actual_away_score')
    if act_h is None or act_a is None:
        continue
        
    vol_h = p.get('home_team_volatility')
    vol_a = p.get('away_team_volatility')
    if vol_h is None or vol_a is None:
        continue
        
    model_total = p.get('model_total')
    if not model_total:
        continue
        
    xpts_h = p.get('xpts_h')
    xpts_a = p.get('xpts_a')
    if xpts_h is None or xpts_a is None:
        continue

    league_id = p.get('league_id')
    home = p.get('home_team')
    away = p.get('away_team')
    
    mae_h, bias_h, graded_h = get_team_stats(home, league_id, lb)
    mae_a, bias_a, graded_a = get_team_stats(away, league_id, lb)
    
    if min(graded_h, graded_a) < 4:
        continue
        
    game = {
        'vol_a': vol_a, 'vol_b': vol_h,
        'mae_a': mae_a, 'mae_b': mae_h,
        'bias_a': bias_a, 'bias_b': bias_h,
        'spread': abs(float(xpts_h) - float(xpts_a))
    }
    
    result = compute_confidence(game)
    band = result['band']['label']
    
    avg_bias_raw = (bias_a + bias_h) / 2
    true_tot = model_total + avg_bias_raw
    actual = float(act_h) + float(act_a)
    
    tiers[band]['g'] += 1
    if actual >= true_tot:
        tiers[band]['w'] += 1
    if actual >= (true_tot - 5):
        tiers[band]['w5'] += 1

print('--- PERFORMANCE BY CONFIDENCE TIER (2026-05-06) ---')
print('  Band        Games   Over TrueTot    Over (TT - 5)')
print('----------------------------------------------------')
for b in ['[ELITE]   ', '[HIGH]    ', '[SOLID]   ', '[MODERATE]', '[LOW]     ', '[AVOID]   ']:
    t = tiers[b]
    if t['g'] > 0:
        w_pct = (t['w']/t['g'])*100
        w5_pct = (t['w5']/t['g'])*100
        print(f"  {b} {t['g']:>4}     {t['w']:>2} ({w_pct:>4.1f}%)       {t['w5']:>2} ({w5_pct:>4.1f}%)")
