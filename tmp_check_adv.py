import json

for lid in [198, 61]:
    try:
        with open(f'data/bball_stats_{lid}_adv.json', encoding='utf-8') as f:
            d = json.load(f)
        teams = d.get('teams', [])
        names = [t['team_name'] for t in teams[:3]]
        print(f'League {lid} ADV: {len(teams)} teams - first 3: {names}')
    except Exception as e:
        print(f'League {lid}: ERROR - {e}')
