import json
d = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))
for team in d:
    if 'Poland' in team.get('country', ''):
        print(team['team_name'])
