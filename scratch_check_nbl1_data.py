import json

data = json.load(open('data/historical/nbl1_official_209.json', 'r', encoding='utf-8'))
print(f'Games in file: {len(data)}')
for i, g in enumerate(data):
    home = g.get('home_team')
    away = g.get('away_team')
    date = g.get('date')
    fid  = g.get('fixture_id')
    hs   = g.get('stats', {}).get('home', {})
    print(f'\nGame {i+1}: {home} vs {away} on {date}')
    print(f'  Score: {g.get("home_score")} - {g.get("away_score")}')
    print(f'  fixture_id: {fid}')
    print(f'  Home FGM={hs.get("fgm")} FGA={hs.get("fga")} PTS={hs.get("pts")} REB={hs.get("reb")} AST={hs.get("ast")}')
    players = hs.get('players', [])
    print(f'  Players: {len(players)}')
    if players:
        print(f'  First player: {players[0]}')
