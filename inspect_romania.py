import json

# Check Romania stats - league 78
data = json.load(open('data/bball_stats_78.json', encoding='utf-8'))
print('League:', data.get('league_id'), '| Model:', data.get('model_architecture'))
print('Teams found:', len(data.get('teams', [])))
print()
for t in data['teams']:
    name = t['team_name']
    gp = t['games_played']
    ao = t['adj_off']
    ad = t['adj_def']
    srs = t['srs_rating']
    print(f'  {name}: {gp}gp | adj_off={ao} | adj_def={ad} | srs={srs}')
print()
print('--- RAW HISTORICAL SCORES ---')
hist = json.load(open('data/historical/proballers_romania-division-a.json', encoding='utf-8'))
print(f'Total games: {len(hist)}')
for g in hist[:10]:
    ht = g['home_team']
    at = g['away_team']
    hs = g.get('home_score', '?')
    as_ = g.get('away_score', '?')
    d = g.get('date', '?')
    print(f'  {ht} {hs} - {as_} {at}  ({d})')
