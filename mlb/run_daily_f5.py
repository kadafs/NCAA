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
LEAGUE_AVG_OPS  = 0.720   # rough MLB average, used to convert OPS -> wRC+ proxy
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

def _calc_ops(stat_dict):
    """Return OPS float from a statsapi team stat dict, or None."""
    try:
        return float(stat_dict.get('ops', 0))
    except Exception:
        return None

def get_today_games():
    today = datetime.datetime.now().strftime("%m/%d/%Y")
    print(f"Fetching MLB schedule for {today}...")
    try:
        schedule = statsapi.schedule(date=today)
        games = []
        for game in schedule:
            if game.get('status') in ['Postponed', 'Cancelled']:
                continue
            
            games.append({
                'game_id': game['game_id'],
                'away_team': game['away_name'],
                'home_team': game['home_name'],
                'away_pitcher': game.get('away_probable_pitcher', 'TBD'),
                'home_pitcher': game.get('home_probable_pitcher', 'TBD')
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

def get_pitcher_fip(pitcher_name):
    """Return a weighted multi-season FIP for the named pitcher."""
    if pitcher_name in ('TBD', '', None):
        return FALLBACK_FIP

    players = statsapi.lookup_player(pitcher_name)
    if not players:
        return FALLBACK_FIP

    player_id = players[0]['id']

    weighted_fip  = 0.0
    total_weight  = 0.0
    season_detail = {}

    # Use the 'people' hydrate endpoint — correctly scoped to this player only
    for season, weight in SEASON_WEIGHTS.items():
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
            fip = _calc_fip(stats)
        except Exception as e:
            fip = None

        season_detail[season] = round(fip, 2) if fip else None
        if fip is not None:
            weighted_fip += fip * weight
            total_weight += weight

    if total_weight == 0:
        return FALLBACK_FIP

    # If some seasons were missing, rescale the remaining weights
    blended = weighted_fip / total_weight
    return round(blended, 2)

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

def get_team_wrc_proxy(team_name):
    """Return a weighted multi-season wRC+ proxy for the named team."""
    if team_name in team_wrc_cache:
        return team_wrc_cache[team_name]

    teams = statsapi.lookup_team(team_name)
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
    wrc_proxy   = round((blended_ops / LEAGUE_AVG_OPS) * 100, 1)
    team_wrc_cache[team_name] = wrc_proxy
    return wrc_proxy

def main():
    games = get_today_games()
    if not games:
        print("No games found.")
        return
        
    print(f"Found {len(games)} games. Grading matchups...")
    
    report_lines = []
    report_lines.append(f"# MLB F5 Predictions - {datetime.datetime.now().strftime('%Y-%m-%d')}")
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
