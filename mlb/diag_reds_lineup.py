import statsapi
from fetch_lineups import get_lineup_for_game, get_batter_pa_rates

games = statsapi.schedule(sportId=1, date='06/15/2026')
mets_game = next((g for g in games if 'Mets' in g['away_name']), None)
lineups = get_lineup_for_game(mets_game['game_id'])

LEAGUE_AVG = {'bb': 0.085, 'k': 0.225, 'hr': 0.030, 'single': 0.150, 'double': 0.048, 'triple': 0.005}
LEAGUE_OBP = LEAGUE_AVG['bb'] + LEAGUE_AVG['hr'] + LEAGUE_AVG['single'] + LEAGUE_AVG['double'] + LEAGUE_AVG['triple']

print(f"League avg OBP-equiv: {LEAGUE_OBP:.3f}\n")

def check_batter(pid, side, pitcher_hand):
    info = statsapi.get('people', {'personIds': pid, 'hydrate': 'currentTeam'})
    name = info['people'][0]['fullName'] if info['people'] else f'PID {pid}'
    
    raw_seasons = {}
    for season in [2024, 2025, 2026]:
        sit = 'vr' if pitcher_hand.upper() == 'L' else 'vl' if pitcher_hand.upper() == 'R' else 'vs'
        sit_code = 'vl' if pitcher_hand.upper() == 'L' else 'vr'
        h = f'stats(group=[hitting],type=statSplits,sitCodes={sit_code},season={season})'
        try:
            raw = statsapi.get('people', {'personIds': pid, 'hydrate': h})
            stats = {}
            for person in raw.get('people', []):
                for grp in person.get('stats', []):
                    splits = grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats: break
            pa = int(stats.get('plateAppearances', 0) or 0)
            if pa >= 10:
                bb = int(stats.get('baseOnBalls', 0) or 0)
                hr = int(stats.get('homeRuns', 0) or 0)
                h_val = int(stats.get('hits', 0) or 0)
                raw_obp = (bb + hr + h_val) / pa
                raw_seasons[season] = {'pa': pa, 'obp': raw_obp}
        except: pass
    
    blended = get_batter_pa_rates(pid, pitcher_hand=pitcher_hand)
    b_obp = blended['bb'] + blended['hr'] + blended['single'] + blended['double'] + blended['triple']
    
    season_str = "  ".join([f"{s}:{d['pa']}PA OBP={d['obp']:.3f}" for s, d in raw_seasons.items()])
    below = "⚠️ BELOW LEAGUE" if b_obp < (LEAGUE_OBP * 0.80) else ""
    print(f"  [{side}] {name} ({pid})")
    print(f"    Seasons: {season_str if season_str else 'NO DATA'}")
    print(f"    Blended OBP={b_obp:.3f}  HR={blended['hr']:.4f}  K={blended['k']:.4f}  {below}")

print("=== REDS (Home) vs Tobias Myers (RHP) ===")
for pid in lineups['home']:
    check_batter(pid, 'Home', 'R')
    print()
