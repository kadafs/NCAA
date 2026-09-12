import json, sys
sys.stdout.reconfigure(encoding='utf-8')

with open('data/football/universal_predictions_2026-09-05.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for p in data.get('predictions', []):
    ht = p.get('home_team', '')
    at = p.get('away_team', '')
    if 'Aston Villa' in ht or 'Aston Villa' in at:
        print(f"Match: {ht} vs {at}")
        print("  kickoff:", p.get('kickoff'))
        print("  xg_home:", p.get('xg_home'), "xg_away:", p.get('xg_away'))
        print("  btts_prob:", p.get('btts_prob'), "over_2_5_prob:", p.get('over_2_5_prob'))
        print("  market_odds:", p.get('market_odds'))
        print("  statsH:", p.get('match_center', {}).get('statsH'))
        print("  statsA:", p.get('match_center', {}).get('statsA'))
