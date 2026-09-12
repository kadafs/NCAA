import json, sys
sys.stdout.reconfigure(encoding='utf-8')

standings = json.load(open('data/football/standings_39_2026.json', 'r', encoding='utf-8'))
print(f"Standings type: {type(standings)}, len: {len(standings)}")
if isinstance(standings, list):
    for row in standings[:10]:
        print(f"  {row.get('rank')}. {row.get('team', {}).get('name')}: played={row.get('all', {}).get('played')}, pts={row.get('points')}, form={row.get('form')}")
