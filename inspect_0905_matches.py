import json, sys
sys.stdout.reconfigure(encoding='utf-8')

f = 'data/football/universal_predictions_2026-09-05.json'
with open(f, 'r', encoding='utf-8') as fp:
    data = json.load(fp)

for p in data.get('predictions', []):
    if p.get('home_team') == 'Newcastle' and p.get('away_team') == 'Bournemouth':
        print("=== Newcastle vs Bournemouth ===")
        print("xg_home:", p.get('xg_home'), "xg_away:", p.get('xg_away'), "xg_total:", p.get('xg_total'))
        print("btts_prob:", p.get('btts_prob'))
        print("over_2_5_prob:", p.get('over_2_5_prob'))
        print("match_center.over_2_5_prob:", p.get('match_center', {}).get('over_2_5_prob'))
        print("market_odds:", p.get('market_odds'))
        print("statsH:", p.get('match_center', {}).get('statsH'))
        print("statsA:", p.get('match_center', {}).get('statsA'))
        break

for p in data.get('predictions', []):
    if p.get('home_team') == 'Manchester City':
        print("=== Manchester City ===")
        print("away:", p.get('away_team'))
        print("xg_home:", p.get('xg_home'), "xg_away:", p.get('xg_away'), "xg_total:", p.get('xg_total'))
        print("btts_prob:", p.get('btts_prob'))
        print("over_2_5_prob:", p.get('over_2_5_prob'))
        print("market_odds:", p.get('market_odds'))
        print("statsH:", p.get('match_center', {}).get('statsH'))
        print("statsA:", p.get('match_center', {}).get('statsA'))
        break
