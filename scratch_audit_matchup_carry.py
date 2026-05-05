import json
import glob
import os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data', 'basketball')
EPOCH = '2026-03-25'

def run():
    files = sorted(glob.glob(os.path.join(DATA_DIR, 'universal_predictions_*.json')))
    files = [f for f in files if os.path.basename(f).split('_')[-1].split('.')[0] >= EPOCH]

    # 1. Build team profiles (Pts/Game, MAE, Volatility)
    team_data = defaultdict(lambda: {'xpts': [], 'actual': [], 'vol_list': []})
    
    for f in files:
        try:
            data = json.load(open(f, encoding='utf-8'))
        except: continue
        for p in data.get('predictions', []):
            if None not in (p.get('actual_home_score'), p.get('xpts_h')):
                team_data[p['home_team']]['actual'].append(p['actual_home_score'])
                team_data[p['home_team']]['xpts'].append(p['xpts_h'])
                if p.get('home_team_volatility'): team_data[p['home_team']]['vol_list'].append(p['home_team_volatility'])
            if None not in (p.get('actual_away_score'), p.get('xpts_a')):
                team_data[p['away_team']]['actual'].append(p['actual_away_score'])
                team_data[p['away_team']]['xpts'].append(p['xpts_a'])
                if p.get('away_team_volatility'): team_data[p['away_team']]['vol_list'].append(p['away_team_volatility'])

    team_profiles = {}
    for team, stats in team_data.items():
        if len(stats['actual']) < 3: continue
        avg_pts = sum(stats['xpts']) / len(stats['xpts'])
        if avg_pts == 0: continue
        
        mae = sum(abs(a - x) for a, x in zip(stats['actual'], stats['xpts'])) / len(stats['actual'])
        vol = sum(stats['vol_list']) / len(stats['vol_list']) if stats['vol_list'] else 15.0
        
        is_elite = (mae <= (avg_pts * 0.10)) and (vol <= (avg_pts * 0.15))
        team_profiles[team] = is_elite

    # 2. Grade games based on Elite participants
    buckets = {
        "BOTH_ELITE": [],
        "ONE_ELITE": [],
        "ZERO_ELITE": []
    }

    for f in files:
        try:
            data = json.load(open(f, encoding='utf-8'))
        except: continue
        for p in data.get('predictions', []):
            act_h = p.get('actual_home_score')
            act_a = p.get('actual_away_score')
            mod_total = p.get('model_total')
            home = p.get('home_team')
            away = p.get('away_team')
            
            if None in (act_h, act_a, mod_total, home, away): continue
            act_total = act_h + act_a
            if home not in team_profiles or away not in team_profiles: continue
            
            elite_count = sum([team_profiles[home], team_profiles[away]])
            error = abs(act_total - mod_total)
            
            if elite_count == 2:
                buckets["BOTH_ELITE"].append(error)
            elif elite_count == 1:
                buckets["ONE_ELITE"].append(error)
            else:
                buckets["ZERO_ELITE"].append(error)

    # 3. Print Results
    print("="*60)
    print(" DO WE NEED TWO ELITE TEAMS? (10% Rule Audit)")
    print("="*60)
    for name, errors in buckets.items():
        if not errors: continue
        avg_err = sum(errors) / len(errors)
        under_10_count = sum(1 for e in errors if e <= 10.0)
        hit_rate = (under_10_count / len(errors)) * 100
        
        print(f"[{name}] - {len(errors)} games")
        print(f"  Avg Game Error: {avg_err:.1f} pts")
        print(f"  Games decided by < 10 pts: {hit_rate:.1f}%")
        print()

if __name__ == '__main__':
    run()
