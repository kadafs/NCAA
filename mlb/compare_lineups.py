from fetch_lineups import get_lineup_for_game, get_batter_pa_rates
from monte_carlo_f5 import generate_generic_lineup
import statsapi

games = statsapi.schedule(sportId=1, date='06/15/2026')
mets_game = next((g for g in games if 'Mets' in g['away_name']), None)
lineups = get_lineup_for_game(mets_game['game_id'])

print('--- REDS (Home) Confirmed Lineup PA Rates vs RHP ---')
total_obp = 0
for pid in lineups['home']:
    r = get_batter_pa_rates(pid, pitcher_hand='R')
    obp = r['bb'] + r['hr'] + r['single'] + r['double'] + r['triple']
    total_obp += obp
    print(f'  PID {pid}: OBP={obp:.3f}  HR={r["hr"]:.4f}  BB={r["bb"]:.4f}  K={r["k"]:.4f}')
avg = total_obp / len(lineups['home'])
print(f'  AVG OBP-equiv: {avg:.3f}')
