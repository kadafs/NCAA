import json, os, sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

leagues = [72, 76, 111, 198, 368, 424]
for lid in leagues:
    for suffix in ['adv', 'srs']:
        path = f'data/bball_stats_{lid}_{suffix}.json'
        if os.path.exists(path):
            d = json.load(open(path, encoding='utf-8'))
            names = [t['team_name'] for t in d.get('teams', [])]
            print(f'[{lid}]:', names)
            break
