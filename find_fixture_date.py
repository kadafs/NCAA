import json, glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for f in glob.glob('data/football/universal_fixtures_*.json'):
    try:
        data = json.load(open(f, 'r', encoding='utf-8'))
        for lid, ldata in data.items():
            for g in ldata.get('games', []):
                if g.get('home_team') == 'Aston Villa' and g.get('away_team') == 'Nottingham Forest':
                    print(f"MATCH FOUND in {f}:")
                    print("  Date:", f)
                    print("  Kickoff:", g.get('kickoff'))
                    print("  Fixture ID:", g.get('fixture_id'))
    except Exception as e:
        pass
