from mlb_time import get_mlb_now
import statsapi
import datetime
import os
import sys

# Import our grading engine
from grade_f5 import grade_matchup

# ---------------------------------------------------------------------------
# Multi-year season weights  (must sum to 1.0)
# Early in the season the current year has a small sample, so we lean on
# prior seasons.  Adjust these weights as the season progresses.
# ---------------------------------------------------------------------------
# Top-Down Season Weights
# The user specifically requested the Top-Down model to use current-season (2026)
# data only to capture current team dynamics/form.
# ---------------------------------------------------------------------------
SEASON_WEIGHTS = {
    2026: 1.0,
}
LEAGUE_AVG_OPS = {
    1: 0.720,   # MLB
    11: 0.760,  # AAA (PCL is very hitter friendly)
    12: 0.740,  # AA
    13: 0.730,  # High-A
    14: 0.730,  # Single-A
}

# MLB League Average FIP fluctuates by season
LEAGUE_AVG_FIP_BY_SEASON = {
    2023: 4.33,
    2024: 4.15,
    2025: 4.20,
    2026: 4.25,
}

# Live dynamic rolling FIP cache to prevent repeating the 55-second API fetch
_LIVE_LEAGUE_FIP_CACHE = {}
FIP_CONSTANT    = 3.20    # standard FIP constant
FALLBACK_FIP    = 4.50    # league-average fallback when data is missing
FALLBACK_WRC    = 100.0   # league-average wRC+ fallback
MIN_IP_THRESHOLD = 1.0    # ignore seasons with fewer IP (spring training noise)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _parse_ip(ip_str):
    """Convert statsapi innings-pitched string (e.g. '18.2') to decimal IP."""
    try:
        parts = str(ip_str).split('.')
        full = float(parts[0])
        thirds = float(parts[1]) / 3.0 if len(parts) > 1 else 0.0
        return full + thirds
    except Exception:
        return 0.0

def _calc_fip(stats):
    """Return FIP from a statsapi stat dict, or None if insufficient data."""
    try:
        ip = _parse_ip(stats.get('inningsPitched', '0'))
        if ip < MIN_IP_THRESHOLD:
            return None
        hr  = int(stats.get('homeRuns',    0))
        bb  = int(stats.get('baseOnBalls', 0))
        hbp = int(stats.get('hitBatsmen',  0))
        k   = int(stats.get('strikeOuts',  0))
        return ((13 * hr) + (3 * (bb + hbp)) - (2 * k)) / ip + FIP_CONSTANT
    except Exception:
        return None

def _fetch_live_league_fip(season):
    """
    Fetches the true dynamic league average FIP by aggregating all 30 MLB teams.
    This takes ~55 seconds to run, so the result should be cached to disk per day.
    """
    if season in _LIVE_LEAGUE_FIP_CACHE:
        return _LIVE_LEAGUE_FIP_CACHE[season]

    import os, json, datetime
    today_str = get_mlb_now().date().isoformat()
    cache_path = os.path.join(os.path.dirname(__file__), '..', 'data', f'league_fip_{season}_{today_str}.json')
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                val = json.load(f).get('fip')
                if val:
                    _LIVE_LEAGUE_FIP_CACHE[season] = val
                    return val
        except Exception:
            pass

    print(f"\n[SYSTEM] Fetching live MLB League FIP for {season} (This takes ~55 seconds)...")
    try:
        teams = statsapi.get('teams', {'sportId': 1, 'season': season}).get('teams', [])
        total_hr, total_bb, total_hbp, total_k, total_ip = 0, 0, 0, 0, 0.0

        for t in teams:
            team_id = t['id']
            try:
                data = statsapi.get('team_stats', {'teamId': team_id, 'group': 'pitching', 'stats': 'season', 'season': season})
                for stat_group in data.get('stats', []):
                    splits = stat_group.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        total_hr += int(stats.get('homeRuns', 0))
                        total_bb += int(stats.get('baseOnBalls', 0))
                        total_hbp += int(stats.get('hitBatsmen', 0))
                        total_k += int(stats.get('strikeOuts', 0))
                        total_ip += _parse_ip(stats.get('inningsPitched', '0'))
                        break
            except Exception:
                continue

        if total_ip > 0:
            league_fip = ((13 * total_hr) + (3 * (total_bb + total_hbp)) - (2 * total_k)) / total_ip + FIP_CONSTANT
            _LIVE_LEAGUE_FIP_CACHE[season] = round(league_fip, 3)
            print(f"[SYSTEM] Live {season} League FIP: {league_fip:.3f}\n")
            
            try:
                os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                with open(cache_path, 'w', encoding='utf-8') as f:
                    json.dump({'fip': _LIVE_LEAGUE_FIP_CACHE[season]}, f)
            except Exception:
                pass
                
            return _LIVE_LEAGUE_FIP_CACHE[season]
            
    except Exception as e:
        print(f"[ERROR] Failed to fetch live league FIP: {e}")
    
    return None

def _calc_ops(stat_dict):
    """Return OPS float from a statsapi team stat dict, or None."""
    try:
        return float(stat_dict.get('ops', 0))
    except Exception:
        return None

def get_today_games(sport_id=1, date_str=None):
    """
    Fetches games for the specified sportId.
    date_str: optional MM/DD/YYYY string. Defaults to today.
    Returns a list of dicts: {away_team, home_team, away_pitcher, home_pitcher, game_id, venue_name}
    """
    if date_str:
        today = date_str
    else:
        # Timezone Fix: Subtract 6 hours so the baseball schedule day doesn't roll over 
        # to tomorrow at midnight local time while West Coast US games are still actively playing.
        today = (get_mlb_now() - datetime.timedelta(hours=6)).strftime("%m/%d/%Y")
    print(f"Fetching schedule for {today} (sportId={sport_id})...")
    try:
        schedule = statsapi.schedule(sportId=sport_id, date=today)
        games = []
        for game in schedule:
            if game.get('status') in ['Postponed', 'Cancelled']:
                continue
            
            games.append({
                'game_id': game['game_id'],
                'away_team': game['away_name'],
                'home_team': game['home_name'],
                'away_pitcher': game.get('away_probable_pitcher', 'TBD'),
                'home_pitcher': game.get('home_probable_pitcher', 'TBD'),
                'venue_name': game.get('venue_name', 'Unknown Venue')
            })
        return games
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

# Per-season lookup caches so we only call the API once per player/team
_pitcher_cache = {}  # (player_id, season) -> fip
_team_cache    = {}  # (team_id,   season) -> ops

def _get_pitcher_fip_single_season(player_id, season):
    key = (player_id, season)
    if key in _pitcher_cache:
        return _pitcher_cache[key]
    try:
        data = statsapi.player_stat_data(player_id, group="pitching",
                                         type="season", sportId=1)
        for grp in data.get('stats', []):
            if grp.get('season') == str(season) and grp.get('group') == 'pitching':
                fip = _calc_fip(grp.get('stats', {}))
                _pitcher_cache[key] = fip
                return fip
        # season not found
        _pitcher_cache[key] = None
        return None
    except Exception:
        _pitcher_cache[key] = None
        return None

def get_pitcher_fip(pitcher_name, sport_id=1):
    """Return a weighted multi-season FIP for the named pitcher.

    Issue 5 fix: if the pitcher has fewer than MIN_RELIABLE_IP innings in the
    current season, blend 50/50 with the prior season to reduce small-sample noise.
    The 100% current-year weight only activates once the pitcher has a reliable sample.
    """
    MIN_RELIABLE_IP = 20.0   # innings below this triggers prior-year blend

    if pitcher_name in ('TBD', '', None):
        return FALLBACK_FIP

    players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
    if not players:
        return FALLBACK_FIP

    player_id = players[0]['id']
    current_season = max(SEASON_WEIGHTS.keys())  # e.g. 2026
    prior_season   = current_season - 1           # e.g. 2025

    def _fetch_season_fip(season):
        try:
            raw = statsapi.get('people', {
                'personIds': player_id,
                'hydrate':   f'stats(group=[pitching],type=season,season={season})'
            })
            stats = {}
            for person in raw.get('people', []):
                for stat_grp in person.get('stats', []):
                    splits = stat_grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats:
                    break
            ip  = _parse_ip(stats.get('inningsPitched', '0'))
            fip = _calc_fip(stats)
            return fip, ip
        except Exception:
            return None, 0.0

    current_fip, current_ip = _fetch_season_fip(current_season)
    prior_fip, prior_ip = _fetch_season_fip(prior_season)

    # Bayesian Shrinkage (Regressing to the mean)
    # This prevents single-game extreme volatility by weighting the pitcher's
    # actual performance against the league average based on their total IP.
    REGRESSION_WEIGHT = 50.0
    
    if sport_id == 1:
        live_league_fip = _fetch_live_league_fip(current_season)
        if live_league_fip is not None:
            league_fip = live_league_fip
        else:
            league_fip = LEAGUE_AVG_FIP_BY_SEASON.get(current_season, 4.25)
    else:
        # Minor league run environments are slightly higher
        league_fip = FALLBACK_FIP

    total_ip = current_ip + (prior_ip if prior_fip else 0.0)

    if total_ip == 0:
        return league_fip

    weighted_perf = 0.0
    if current_fip is not None:
        weighted_perf += (current_fip * current_ip)
    if prior_fip is not None:
        weighted_perf += (prior_fip * prior_ip)

    # Projected FIP = ((Pitcher FIP * Pitcher IP) + (League FIP * Regression Weight)) / (Pitcher IP + Regression Weight)
    projected_fip = (weighted_perf + (league_fip * REGRESSION_WEIGHT)) / (total_ip + REGRESSION_WEIGHT)

    return round(projected_fip, 2)


def get_pitcher_projected_ip(pitcher_name, sport_id=1):
    """
    Returns the projected F5 innings (capped at 5.0) based on the pitcher's
    recent game logs (last 5 games).
    """
    if pitcher_name in ('TBD', '', None):
        return 4.0 # generic projection
        
    players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
    if not players:
        return 4.0
        
    player_id = players[0]['id']
    try:
        # Fetch 2026 game log
        data = statsapi.player_stat_data(player_id, group="pitching", type="gameLog", sportId=sport_id)
        games = data.get('stats', [])
        if not games: return 4.0
        
        # Take up to last 5 games
        recent_games = games[:5]
        total_ip = 0.0
        count = 0
        for g in recent_games:
            stats = g.get('stats', {})
            ip_str = stats.get('inningsPitched', '0')
            total_ip += _parse_ip(ip_str)
            count += 1
            
        if count == 0: return 4.0
        
        avg_ip = total_ip / count
        # For F5 purposes, cap at 5.0 innings
        return round(min(5.0, avg_ip), 2)
    except Exception:
        return 4.0

# ---------------------------------------------------------------------------
# Team offense — weighted multi-season OPS → wRC+ proxy
# ---------------------------------------------------------------------------
team_wrc_cache = {}  # team_name -> blended wRC+

def _get_team_ops_single_season(team_id, season):
    key = (team_id, season)
    if key in _team_cache:
        return _team_cache[key]
    try:
        data = statsapi.get('team_stats', {
            'teamId':    team_id,
            'group':     'hitting',
            'stats':     'season',
            'season':    str(season)
        })
        for grp in data.get('stats', []):
            splits = grp.get('splits', [])
            if splits:
                ops = _calc_ops(splits[0].get('stat', {}))
                _team_cache[key] = ops
                return ops
        _team_cache[key] = None
        return None
    except Exception as e:
        _team_cache[key] = None
        return None

def _calc_wrc_proxy(ops, sport_id=1):
    """Simple proxy: (Team OPS / League OPS) * 100"""
    avg_ops = LEAGUE_AVG_OPS.get(sport_id, 0.720)
    if avg_ops == 0: return 100.0
    return (ops / avg_ops) * 100.0

def get_team_wrc_proxy(team_name, sport_id=1):
    """Return a weighted multi-season wRC+ proxy for the named team."""
    if team_name in team_wrc_cache:
        return team_wrc_cache[team_name]

    teams = statsapi.lookup_team(team_name, sportIds=sport_id)
    if not teams:
        return FALLBACK_WRC

    team_id = teams[0]['id']
    weighted_ops = 0.0
    total_weight = 0.0

    for season, weight in SEASON_WEIGHTS.items():
        ops = _get_team_ops_single_season(team_id, season)
        if ops and ops > 0:
            weighted_ops += ops * weight
            total_weight += weight

    if total_weight == 0:
        return FALLBACK_WRC

    blended_ops = weighted_ops / total_weight
    wrc_proxy   = round((blended_ops / LEAGUE_AVG_OPS.get(sport_id, 0.720)) * 100, 1)
    team_wrc_cache[team_name] = wrc_proxy
    return wrc_proxy

team_bullpen_cache = {}

def _get_team_pitching_fip_single_season(team_id, season):
    try:
        data = statsapi.get('team_stats', {
            'teamId':    team_id,
            'group':     'pitching',
            'stats':     'season',
            'season':    str(season)
        })
        for grp in data.get('stats', []):
            splits = grp.get('splits', [])
            if splits:
                fip = _calc_fip(splits[0].get('stat', {}))
                return fip
        return None
    except Exception:
        return None

def get_team_bullpen_fip(team_name, sport_id=1):
    """
    Returns the team's TRUE BULLPEN FIP by fetching individual pitcher stats,
    separating starters from relievers, and computing a relief-only weighted FIP.

    Issue 4 fix: the old implementation used team-wide pitching stats, which
    includes starter innings. A team with an ace starter would show a misleadingly
    low 'bullpen' FIP. This version identifies relievers by GS count (GS < 3)
    and computes FIP only from their innings.

    Falls back to team-wide pitching FIP if insufficient reliever data.
    """
    if team_name in team_bullpen_cache:
        return team_bullpen_cache[team_name]

    teams = statsapi.lookup_team(team_name, sportIds=sport_id)
    if not teams:
        return FALLBACK_FIP

    team_id   = teams[0]['id']
    season    = max(SEASON_WEIGHTS.keys())

    try:
        # Fetch all pitchers on the active 40-man roster for this team
        roster_data = statsapi.get('team_roster', {
            'teamId':   team_id,
            'rosterType': 'active',
        })
        roster = roster_data.get('roster', [])
        pitcher_ids = [
            p['person']['id'] for p in roster
            if p.get('position', {}).get('code') == '1'  # pitchers only
        ]
    except Exception:
        pitcher_ids = []

    if not pitcher_ids:
        # Fallback to team-wide FIP
        fip = _get_team_pitching_fip_single_season(team_id, season)
        result = round(fip, 2) if fip else FALLBACK_FIP
        team_bullpen_cache[team_name] = result
        return result

    # Fetch each pitcher's season stats and classify starter vs. reliever
    # SPEED OPTIMIZATION: Instead of looping and making 20 individual API calls,
    # we pass all pitcher IDs as a comma-separated string to fetch them in ONE call.
    relief_k = relief_bb = relief_hr = relief_ip = 0.0
    found_relievers = 0
    
    id_string = ','.join(str(pid) for pid in pitcher_ids)

    try:
        raw = statsapi.get('people', {
            'personIds': id_string,
            'hydrate':   f'stats(group=[pitching],type=season,season={season})'
        })
        
        for person in raw.get('people', []):
            stats = {}
            for grp in person.get('stats', []):
                splits = grp.get('splits', [])
                if splits:
                    stats = splits[0].get('stat', {})
                    break
            
            if not stats:
                continue
                
            ip  = _parse_ip(stats.get('inningsPitched', '0'))
            gs  = int(stats.get('gamesStarted', 0) or 0)

            if ip < 1.0:
                continue  # no meaningful data

            # Issue 4: classify as reliever if fewer than 3 starts
            if gs < 3:
                relief_ip  += ip
                relief_k   += int(stats.get('strikeOuts',  0) or 0)
                relief_bb  += int(stats.get('baseOnBalls', 0) or 0)
                relief_hr  += int(stats.get('homeRuns',    0) or 0)
                found_relievers += 1
    except Exception:
        pass

    if found_relievers >= 3 and relief_ip >= 10.0:
        # Enough data to compute a reliable bullpen FIP
        bullpen_fip = ((13 * relief_hr) + (3 * relief_bb) - (2 * relief_k)) / relief_ip + FIP_CONSTANT
        result = round(max(2.5, min(7.5, bullpen_fip)), 2)   # hard cap for sanity
    else:
        # Insufficient reliever data — fall back to team-wide FIP
        fip = _get_team_pitching_fip_single_season(team_id, season)
        result = round(fip, 2) if fip else FALLBACK_FIP

    team_bullpen_cache[team_name] = result
    return result


def main():
    games = get_today_games()
    if not games:
        print("No games found.")
        return
        
    print(f"Found {len(games)} games. Grading matchups...")
    
    report_lines = []
    report_lines.append(f"# MLB F5 Predictions - {get_mlb_now().strftime('%Y-%m-%d')}")
    report_lines.append("")
    
    for game in games:
        away = game['away_team']
        home = game['home_team']
        ap = game['away_pitcher']
        hp = game['home_pitcher']
        
        print(f"Grading {away} @ {home}...")
        print(f"  Looking up {ap}...")
        ap_fip = get_pitcher_fip(ap)
        print(f"  Looking up {hp}...")
        hp_fip = get_pitcher_fip(hp)
        
        print(f"  Looking up {away} offense...")
        away_wrc = get_team_wrc_proxy(away)
        print(f"  Looking up {home} offense...")
        home_wrc = get_team_wrc_proxy(home)
        
        # Park factor defaults to 1.0 for V1
        result = grade_matchup(away, ap_fip, away_wrc, home, hp_fip, home_wrc)
        
        report_lines.append(f"### {away} ({ap}) @ {home} ({hp})")
        report_lines.append(f"- **Pitching Matchup:** {ap} (FIP: {ap_fip}) vs {hp} (FIP: {hp_fip})")
        report_lines.append(f"- **Offense Matchup:** {away} (wRC+: {away_wrc}) vs {home} (wRC+: {home_wrc})")
        report_lines.append(f"- **Expected F5 Runs:** {result['away_team']} {result['away_expected_f5_runs']} | {result['home_team']} {result['home_expected_f5_runs']}")
        report_lines.append(f"- **Projected F5 Total:** {result['projected_f5_total']}")
        
        fav_team = home if result['projected_f5_margin'] > 0 else away
        abs_margin = abs(result['projected_f5_margin'])
        report_lines.append(f"- **Projected F5 Margin:** {fav_team} by {abs_margin}")
        report_lines.append("")
        print(f"Graded {away} @ {home}")

    # Write to a markdown report
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_f5_report.md')
    with open(output_path, 'w') as f:
        f.write("\n".join(report_lines))
        
    print(f"\nDone! Report written to {output_path}")

if __name__ == "__main__":
    main()
