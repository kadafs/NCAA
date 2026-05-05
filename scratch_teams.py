import json
d = json.load(open('data/bball_stats_72_adv.json', encoding='utf-8'))
for t in d.get('teams', []):
    print(t.get('team_name').encode('ascii', 'ignore').decode('ascii'))
