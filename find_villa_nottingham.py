import json, sys
sys.stdout.reconfigure(encoding='utf-8')

for date in ['2026-09-06', '2026-09-09', '2026-09-02', '2026-08-31', '2026-08-30']:
    f = f'data/football/universal_predictions_{date}.json'
    try:
        with open(f, 'r', encoding='utf-8') as fp:
            data = json.load(fp)
        for p in data.get('predictions', []):
            if 'Aston Villa' in p.get('home_team', '') and 'Nottingham' in p.get('away_team', ''):
                print(f"MATCH FOUND in {f}:")
                print("  Date:", p.get('date'), "Kickoff:", p.get('kickoff'))
                print("  Home:", p.get('home_team'), "Away:", p.get('away_team'))
                print("  1X2:", p.get('home_win_prob'), p.get('draw_prob_1x2'), p.get('away_win_prob'))
                print("  btts_prob:", p.get('btts_prob'))
                print("  over_2_5_prob:", p.get('over_2_5_prob'))
                print("  match_center.over_2_5_prob:", p.get('match_center', {}).get('over_2_5_prob'))
                print("  statsH:", p.get('match_center', {}).get('statsH'))
                print("  statsA:", p.get('match_center', {}).get('statsA'))
                print("  market_odds:", p.get('market_odds'))
                break
    except Exception as e:
        pass
