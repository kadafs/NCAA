import statsapi
from fetch_lineups import get_lineup_for_game, get_batter_pa_rates

games = statsapi.schedule(sportId=1, date='06/15/2026')
game = next((g for g in games if 'Athletics' in g['home_name'] or 'Athletics' in g['away_name']), None)
if not game:
    print("No Athletics game found")
    exit()
print(f"Game: {game['away_name']} @ {game['home_name']}")
lineups = get_lineup_for_game(game['game_id'])

LEAGUE_OBP = 0.085 + 0.030 + 0.150 + 0.048 + 0.005

for side, ids, pitcher_hand, label in [
    ('Away (Pirates)', lineups['away'], 'R', 'vs RHP'),
    ('Home (Athletics)', lineups['home'], 'R', 'vs RHP'),
]:
    print(f"\n--- {side} lineup {label} ---")
    total_obp = 0
    for pid in ids:
        info = statsapi.get('people', {'personIds': pid, 'hydrate': 'currentTeam'})
        name = info['people'][0]['fullName'] if info['people'] else f'PID {pid}'
        r = get_batter_pa_rates(pid, pitcher_hand=pitcher_hand)
        obp = r['bb'] + r['hr'] + r['single'] + r['double'] + r['triple']
        total_obp += obp
        print(f"  {name}: OBP={obp:.3f}  HR={r['hr']:.4f}  BB={r['bb']:.4f}  K={r['k']:.4f}")
    if ids:
        print(f"  AVG OBP: {total_obp/len(ids):.3f}")
