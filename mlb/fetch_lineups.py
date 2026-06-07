"""
fetch_lineups.py
Fetches today's confirmed batting lineups from the MLB StatsAPI.
Falls back gracefully when lineups haven't been posted yet.
"""
import statsapi


def get_lineup_for_game(game_id):
    """
    Returns {'away': [player_id, ...], 'home': [player_id, ...]}
    in batting order (1-9). Returns empty lists if lineup not yet posted.
    """
    try:
        data = statsapi.get('game', {
            'gamePk':  game_id,
            'hydrate': 'lineups'
        })
        lineups = data.get('liveData', {}).get('lineups', {})
        away_ids = [p['id'] for p in lineups.get('awayPlayers', [])]
        home_ids = [p['id'] for p in lineups.get('homePlayers', [])]
        return {'away': away_ids, 'home': home_ids}
    except Exception:
        return {'away': [], 'home': []}


def get_batter_pa_rates(player_id):
    """
    Returns a dict of plate appearance outcome rates for a batter,
    blended across 2024/2025/2026 seasons using the same weights as run_daily_f5.py.

    Keys: bb_rate, k_rate, hr_rate, single_rate, double_rate, triple_rate, out_rate
    All values are per-PA probabilities that sum to ~1.0.
    """
    # Monte Carlo uses historical data to determine true talent
    MC_WEIGHTS = {
        2026: 0.40,
        2025: 0.40,
        2024: 0.20,
    }

    LEAGUE_AVG = {
        'bb':     0.085,
        'k':      0.225,
        'hr':     0.030,
        'single': 0.150,
        'double': 0.048,
        'triple': 0.005,
    }

    weighted = {k: 0.0 for k in LEAGUE_AVG}
    total_weight = 0.0

    for season, weight in MC_WEIGHTS.items():
        try:
            raw = statsapi.get('people', {
                'personIds': player_id,
                'hydrate':   f'stats(group=[hitting],type=season,season={season})'
            })
            stats = {}
            for person in raw.get('people', []):
                for grp in person.get('stats', []):
                    splits = grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats:
                    break

            pa  = int(stats.get('plateAppearances', 0) or 0)
            if pa < 10:
                continue  # too small a sample — skip this season

            bb  = int(stats.get('baseOnBalls', 0) or 0)
            k   = int(stats.get('strikeOuts',  0) or 0)
            hr  = int(stats.get('homeRuns',    0) or 0)
            h   = int(stats.get('hits',        0) or 0)
            dbl = int(stats.get('doubles',     0) or 0)
            trp = int(stats.get('triples',     0) or 0)
            sng = h - hr - dbl - trp

            rates = {
                'bb':     bb  / pa,
                'k':      k   / pa,
                'hr':     hr  / pa,
                'single': max(sng, 0) / pa,
                'double': dbl / pa,
                'triple': trp / pa,
            }
            for k_name in weighted:
                weighted[k_name] += rates[k_name] * weight
            total_weight += weight

        except Exception:
            continue

    if total_weight == 0:
        # No data — return league averages
        out = dict(LEAGUE_AVG)
        out['out_rate'] = 1.0 - sum(LEAGUE_AVG.values())
        return out

    # Rescale to actual weight collected
    result = {k: weighted[k] / total_weight for k in weighted}
    result['out_rate'] = max(0.0, 1.0 - sum(result.values()))
    return result


def get_pitcher_pa_modifiers(pitcher_fip, pitcher_player_id=None):
    """
    Returns a modifier dict that scales batter PA rates to reflect the
    opposing pitcher's quality. Uses FIP components as a proxy.

    modifiers: {'k': float, 'bb': float, 'hr': float}
    A modifier of 1.2 means the pitcher inflates that outcome by 20%.
    """
    # League averages as baseline
    LEAGUE_K_PER_9  = 8.8
    LEAGUE_BB_PER_9 = 3.1
    LEAGUE_HR_PER_9 = 1.2

    if pitcher_player_id is None:
        return {'k': 1.0, 'bb': 1.0, 'hr': 1.0}

    # Monte Carlo uses historical data to determine true talent
    MC_WEIGHTS = {
        2026: 0.40,
        2025: 0.40,
        2024: 0.20,
    }

    k_total = bb_total = hr_total = ip_total = 0.0
    w_total = 0.0

    for season, weight in MC_WEIGHTS.items():
        try:
            raw = statsapi.get('people', {
                'personIds': pitcher_player_id,
                'hydrate':   f'stats(group=[pitching],type=season,season={season})'
            })
            stats = {}
            for person in raw.get('people', []):
                for grp in person.get('stats', []):
                    splits = grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats:
                    break

            ip_str = str(stats.get('inningsPitched', '0'))
            parts  = ip_str.split('.')
            ip     = float(parts[0]) + (float(parts[1]) / 3.0 if len(parts) > 1 else 0)
            if ip < 1:
                continue

            k_total  += int(stats.get('strikeOuts',  0) or 0) * weight
            bb_total += int(stats.get('baseOnBalls', 0) or 0) * weight
            hr_total += int(stats.get('homeRuns',    0) or 0) * weight
            ip_total += ip * weight
            w_total  += weight
        except Exception:
            continue

    if ip_total == 0 or w_total == 0:
        return {'k': 1.0, 'bb': 1.0, 'hr': 1.0}

    pitcher_k_per9  = (k_total  / ip_total) * 9
    pitcher_bb_per9 = (bb_total / ip_total) * 9
    pitcher_hr_per9 = (hr_total / ip_total) * 9

    # Use FIP as a proxy for the pitcher's general ability to suppress hits
    hit_mod = pitcher_fip / 4.00

    return {
        'k':  max(0.4, min(2.5, pitcher_k_per9  / LEAGUE_K_PER_9)),
        'bb': max(0.4, min(3.0, pitcher_bb_per9 / LEAGUE_BB_PER_9)),
        'hr': max(0.4, min(4.0, pitcher_hr_per9 / LEAGUE_HR_PER_9)),
        'hit_mod': max(0.6, min(1.8, hit_mod))
    }


if __name__ == '__main__':
    import datetime
    today = datetime.datetime.now().strftime('%m/%d/%Y')
    schedule = statsapi.schedule(date=today)
    if schedule:
        game = schedule[0]
        gid  = game['game_id']
        print(f"Testing lineups for game {gid}: {game['away_name']} @ {game['home_name']}")
        lineups = get_lineup_for_game(gid)
        print(f"  Away lineup IDs: {lineups['away'][:3]}...")
        print(f"  Home lineup IDs: {lineups['home'][:3]}...")
        if lineups['away']:
            pid = lineups['away'][0]
            rates = get_batter_pa_rates(pid)
            print(f"  Batter {pid} PA rates: {rates}")
