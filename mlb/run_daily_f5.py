from mlb_time import get_mlb_now
import statsapi
import datetime
import os
import sys

# Import our grading engine
from grade_f5 import grade_matchup_v6

# Velocity trend engine (Statcast — silent fallback if unavailable)
try:
    from velocity_engine import get_velocity_fip_adjustment
except Exception:
    def get_velocity_fip_adjustment(name): return 0.0

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


def _calc_xfip(stats, league_season=2026):
    """Return xFIP from a statsapi stat dict, normalizing home run variance."""
    try:
        ip = _parse_ip(stats.get('inningsPitched', '0'))
        if ip < MIN_IP_THRESHOLD:
            return None
            
        bb  = int(stats.get('baseOnBalls', 0))
        hbp = int(stats.get('hitBatsmen',  0))
        k   = int(stats.get('strikeOuts',  0))
        
        bf = stats.get('battersFaced', 0)
        fb = stats.get('flyOuts', 0) or stats.get('airOuts', 0) or (bf * 0.25)
        
        expected_hr = fb * 0.105
        
        return ((13 * expected_hr) + (3 * (bb + hbp)) - (2 * k)) / ip + FIP_CONSTANT
    except Exception:
        return None


def _calc_siera(stats):
    """
    Calculate True SIERA using foundational components and batted-ball data.
    The official formula relies on Net GB% (GB - FB - PU).
    Since airOuts encompasses FB and PU, (groundOuts - airOuts) proxies NetGB.
    We scale the out ratio to the total balls in play to derive true NetGB/PA.
    """
    try:
        ip = _parse_ip(stats.get('inningsPitched', '0'))
        if ip < MIN_IP_THRESHOLD:
            return None
        
        bb  = int(stats.get('baseOnBalls', 0))
        hbp = int(stats.get('hitBatsmen',  0))
        k   = int(stats.get('strikeOuts',  0))
        bf  = int(stats.get('battersFaced', 0))
        
        if bf == 0:
            return None
            
        k_pct = k / bf
        bb_pct = (bb + hbp) / bf
        
        # Batted Ball Extraction
        gb_outs = float(stats.get('groundOuts', 0))
        air_outs = float(stats.get('airOuts', 0)) # Includes FB and PU
        
        total_outs = gb_outs + air_outs
        if total_outs > 0:
            # Ratio of net groundballs to total out-producing batted balls
            net_gb_ratio = (gb_outs - air_outs) / total_outs
        else:
            net_gb_ratio = 0.0 # Neutral fallback if no batted balls recorded
            
        # Total Balls in Play = PA - K - BB/HBP - HR
        # (Using HR=0 as minor simplification if HR not fetched, but usually it is)
        hr = int(stats.get('homeRuns', 0))
        bip = max(0, bf - k - bb - hbp - hr)
        
        # NetGB / PA
        net_gb_pa = (net_gb_ratio * bip) / bf
        
        # True SIERA Formula
        siera = (
            6.145 
            - (16.986 * k_pct) 
            + (11.434 * bb_pct) 
            - (1.858 * net_gb_pa) 
            + (7.653 * (k_pct ** 2)) 
            - (6.664 * (net_gb_pa ** 2)) 
            + (10.130 * k_pct * net_gb_pa) 
            - (5.195 * bb_pct * net_gb_pa)
        )
        return siera
    except Exception:
        return None
def _get_rolling_start_fip(player_id, n=5):
    """
    Computes FIP from the pitcher's last N starts using their game log.
    Returns (rolling_fip, starts_used) or (None, 0) on failure.
    """
    try:
        data = statsapi.player_stat_data(player_id, group="pitching", type="gameLog", sportId=1)
        games = data.get('stats', [])
        if not games:
            return None, 0

        # Filter to starts only (gamesStarted == 1)
        starts = [g for g in games if int(g.get('stats', {}).get('gamesStarted', 0)) == 1]
        recent = starts[:n]
        if not recent:
            return None, 0

        total_hr, total_bb, total_hbp, total_k, total_ip = 0, 0, 0, 0, 0.0
        for g in recent:
            s = g.get('stats', {})
            total_ip  += _parse_ip(s.get('inningsPitched', '0'))
            total_hr  += int(s.get('homeRuns',    0))
            total_bb  += int(s.get('baseOnBalls', 0))
            total_hbp += int(s.get('hitBatsmen',  0))
            total_k   += int(s.get('strikeOuts',  0))

        if total_ip < 1.0:
            return None, 0

        rolling_fip = ((13 * total_hr) + (3 * (total_bb + total_hbp)) - (2 * total_k)) / total_ip + FIP_CONSTANT
        return round(rolling_fip, 2), len(recent)
    except Exception:
        return None, 0


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
                'away_id': game.get('away_id'),
                'home_id': game.get('home_id'),
                'away_abbr': game.get('away_file_code', game['away_name'][:3].upper()),
                'home_abbr': game.get('home_file_code', game['home_name'][:3].upper()),
                'away_pitcher': game.get('away_probable_pitcher') or 'TBD',
                'home_pitcher': game.get('home_probable_pitcher') or 'TBD',
                'away_pitcher_id': game.get('away_pitcher_id'),
                'home_pitcher_id': game.get('home_pitcher_id'),
                'venue_name': game.get('venue_name', 'Unknown Venue')
            })
        return games
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

# ---------------------------------------------------------------------------
# Recent F5 Team Form Factor
# ---------------------------------------------------------------------------
# Session-level cache: {team_id: form_factor} — reset each time the process runs
_f5_form_cache = {}

# 2026 MLB baseline: average F5 runs scored per team per game
MLB_F5_BASELINE = 2.30

def get_team_f5_form_factor(team_id: int, n_games: int = 5) -> dict:
    """
    Computes a recent-form multiplier for a team's F5 offensive output.

    Fetches the last n_games+1 Final games, trims the highest single-game
    outlier (to suppress blowout noise), averages the remaining F5 runs
    scored, then blends 50% toward neutral (1.0) for stability.

    Clamped to [0.55, 1.45] before blending.

    Returns
    -------
    dict with keys:
        'factor'      : float (effective multiplier, after 50% blend)
        'raw_avg'     : float (trimmed average F5 runs scored)
        'games_used'  : int
        'games_raw'   : list[int] (all F5 runs scored before trim)
    """
    if team_id in _f5_form_cache:
        return _f5_form_cache[team_id]

    neutral = {'factor': 1.0, 'raw_avg': MLB_F5_BASELINE, 'games_used': 0, 'games_raw': []}

    try:
        today   = (get_mlb_now() - datetime.timedelta(hours=6)).date()
        start   = today - datetime.timedelta(days=21)
        games   = statsapi.schedule(
            sportId=1, team=team_id,
            start_date=start.strftime('%Y-%m-%d'),
            end_date=(today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        )

        final_games = [g for g in reversed(games) if g.get('status') == 'Final']
        recent      = final_games[: n_games + 1]   # +1 so we can trim one outlier

        if len(recent) < 2:
            _f5_form_cache[team_id] = neutral
            return neutral

        f5_list = []
        for g in recent:
            gid     = g['game_id']
            is_home = (g.get('home_id') == team_id)
            try:
                feed    = statsapi.get('game', {
                    'gamePk': gid,
                    'fields': 'liveData,linescore,innings,runs,away,home'
                })
                innings = feed['liveData']['linescore']['innings']
                side    = 'home' if is_home else 'away'
                f5_list.append(sum(i[side].get('runs', 0) for i in innings[:5]))
            except Exception:
                continue

        if len(f5_list) < 2:
            _f5_form_cache[team_id] = neutral
            return neutral

        raw_list = list(f5_list)  # keep full list for reporting

        # Trim highest outlier when we have enough samples
        trimmed = sorted(f5_list)[:-1] if len(f5_list) > 3 else f5_list

        recent_avg   = sum(trimmed) / len(trimmed)
        raw_factor   = recent_avg / MLB_F5_BASELINE
        clamped      = max(0.55, min(1.45, raw_factor))
        # 50% blend toward neutral
        effective    = round(0.50 + 0.50 * clamped, 3)

        result = {
            'factor':     effective,
            'raw_avg':    round(recent_avg, 2),
            'games_used': len(trimmed),
            'games_raw':  raw_list,
        }
        _f5_form_cache[team_id] = result
        return result

    except Exception as e:
        print(f"  [F5 Form] Error for team {team_id}: {e} — using neutral")
        _f5_form_cache[team_id] = neutral
        return neutral


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

def get_pitcher_fip(pitcher_name, sport_id=1, player_id=None):
    """Return a weighted multi-season FIP for the named pitcher.

    Issue 5 fix: if the pitcher has fewer than MIN_RELIABLE_IP innings in the
    current season, blend 50/50 with the prior season to reduce small-sample noise.
    The 100% current-year weight only activates once the pitcher has a reliable sample.
    """
    MIN_RELIABLE_IP = 20.0   # innings below this triggers prior-year blend

    if pitcher_name in ('TBD', '', None):
        return FALLBACK_FIP

    if player_id is None:
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
                'hydrate':   f'stats(group=[pitching],type=season,season={season},sportId={sport_id})'
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
    bayesian_fip = (weighted_perf + (league_fip * REGRESSION_WEIGHT)) / (total_ip + REGRESSION_WEIGHT)

    # ── Rolling Form Blend ──────────────────────────────────────────────────
    # Blend 60% recent (last 5 starts) + 40% Bayesian season FIP.
    # Only applies for MLB starters with enough recent data (>=3 starts).
    # Falls back to pure Bayesian if rolling data is unavailable.
    if sport_id == 1:
        rolling_fip, starts_used = _get_rolling_start_fip(player_id, n=5)
        if rolling_fip is not None and starts_used >= 3:
            rolling_fip_clamped = max(2.5, min(7.5, rolling_fip))
            base_fip = round((rolling_fip_clamped * 0.60) + (bayesian_fip * 0.40), 2)
        else:
            base_fip = round(bayesian_fip, 2)

        # ── Velocity Trend Adjustment ────────────────────────────────────────
        # Add Statcast-based FIP penalty when fastball velo is declining.
        # Silently skipped if Baseball Savant is unreachable.
        velo_adj = get_velocity_fip_adjustment(pitcher_name)
        final_fip = round(min(8.0, base_fip + velo_adj), 2)
        return final_fip

    return round(bayesian_fip, 2)



def get_pitcher_projected_ip(pitcher_name, sport_id=1, player_id=None):
    """
    Returns the projected F5 innings (capped at 5.0) based on the pitcher's
    recent game logs (last 5 starts), adjusted for days rest.
    """
    if pitcher_name in ('TBD', '', None):
        return 4.0  # generic projection

    if player_id is None:
        players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
        if not players:
            return 4.0
        player_id = players[0]['id']
    try:
        # Fetch game log
        data = statsapi.player_stat_data(player_id, group="pitching", type="gameLog", sportId=sport_id)
        games = data.get('stats', [])
        if not games:
            return 4.0

        # Filter to starts only
        starts = [g for g in games if int(g.get('stats', {}).get('gamesStarted', 0)) == 1]
        if not starts:
            # Relief pitcher or no starts — fall back using all game entries
            starts = games

        recent_starts = starts[:5]
        total_ip = 0.0
        count = 0
        for g in recent_starts:
            ip_str = g.get('stats', {}).get('inningsPitched', '0')
            total_ip += _parse_ip(ip_str)
            count += 1

        if count == 0:
            return 4.0

        avg_ip = total_ip / count

        # ── Days-Rest Modifier ────────────────────────────────────────────────
        # Adjust projected IP based on how many days rest the pitcher has.
        # The last start date is in starts[0]['date'] (format: 'YYYY-MM-DD').
        rest_modifier = 1.0
        if sport_id == 1 and starts:
            try:
                last_start_str = starts[0].get('date', '')
                if last_start_str:
                    last_date = datetime.date.fromisoformat(last_start_str)
                    today = get_mlb_now().date()
                    days_rest = (today - last_date).days - 1  # subtract game day itself
                    if days_rest <= 3:
                        rest_modifier = 0.88   # short rest → pulled early
                    elif days_rest == 4:
                        rest_modifier = 1.00   # normal rest → no change
                    elif days_rest <= 6:
                        rest_modifier = 1.05   # extra rest → may go deeper
                    else:
                        rest_modifier = 0.85   # return from IL / very long layoff
            except Exception:
                pass

        adjusted_ip = avg_ip * rest_modifier
        return round(min(5.0, adjusted_ip), 2)
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

def _get_team_ops_split_single_season(team_id, season, sit_code):
    try:
        data = statsapi.get('team_stats', {
            'teamId':    team_id,
            'group':     'hitting',
            'stats':     'statSplits',
            'sitCodes':  sit_code,
            'season':    str(season)
        })
        for grp in data.get('stats', []):
            splits = grp.get('splits', [])
            if splits:
                return _calc_ops(splits[0].get('stat', {}))
        return None
    except Exception:
        return None

def get_team_wrc_splits(team_name, sport_id=1):
    """Return a dict of multi-season wRC+ proxies for vsL and vsR."""
    teams = statsapi.lookup_team(team_name, sportIds=sport_id)
    if not teams:
        return {'vsL': FALLBACK_WRC, 'vsR': FALLBACK_WRC}
    
    team_id = teams[0]['id']
    avg_ops = LEAGUE_AVG_OPS.get(sport_id, 0.720)
    
    def _calc_split(sit_code):
        weighted_ops = 0.0
        total_weight = 0.0
        for season, weight in SEASON_WEIGHTS.items():
            ops = _get_team_ops_split_single_season(team_id, season, sit_code)
            if ops and ops > 0:
                weighted_ops += ops * weight
                total_weight += weight
        if total_weight == 0:
            return FALLBACK_WRC
        return round(((weighted_ops / total_weight) / avg_ops) * 100, 1)

    return {
        'vsL': _calc_split('vl'),
        'vsR': _calc_split('vr')
    }

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
        
        # Pass clean, verified IDs straight through the pipeline
        ap_id = game.get('away_pitcher_id')
        hp_id = game.get('home_pitcher_id')
        
        print(f"Grading {away} @ {home}...")
        print(f"  Looking up {ap}...")
        ap_fip = get_pitcher_fip(ap, player_id=ap_id)
        print(f"  Looking up {hp}...")
        hp_fip = get_pitcher_fip(hp, player_id=hp_id)
        
        print(f"  Looking up {away} offense...")
        away_wrc = get_team_wrc_proxy(away)
        print(f"  Looking up {home} offense...")
        home_wrc = get_team_wrc_proxy(home)
        
        # Park factor defaults to 1.0 for V1
        ap_ip = get_pitcher_projected_ip(ap, player_id=ap_id)
        hp_ip = get_pitcher_projected_ip(hp, player_id=hp_id)
        away_bp = get_team_bullpen_fip(away)
        home_bp = get_team_bullpen_fip(home)
        away_splits = get_team_wrc_splits(away)
        home_splits = get_team_wrc_splits(home)

        result = grade_matchup_v6(
            away, ap_fip, away_bp, ap_ip, away_splits['vsR'], away_splits['vsL'],
            home, hp_fip, home_bp, hp_ip, home_splits['vsR'], home_splits['vsL']
        )
        
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


def get_pitcher_xfip(pitcher_name, sport_id=1, player_id=None):
    """Return a weighted multi-season xFIP for the named pitcher."""
    MIN_RELIABLE_IP = 20.0
    if pitcher_name in ('TBD', '', None): return FALLBACK_FIP
    if player_id is None:
        players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
        if not players: return FALLBACK_FIP
        player_id = players[0]['id']
        
    current_season = max(SEASON_WEIGHTS.keys())
    prior_season   = current_season - 1

    def _fetch_season_xfip(season):
        try:
            raw = statsapi.get('people', {'personIds': player_id, 'hydrate': f'stats(group=[pitching],type=season,season={season},sportId={sport_id})'})
            stats = {}
            for person in raw.get('people', []):
                for stat_grp in person.get('stats', []):
                    splits = stat_grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats: break
            ip  = _parse_ip(stats.get('inningsPitched', '0'))
            xfip = _calc_xfip(stats)
            return xfip, ip
        except Exception:
            return None, 0.0

    current_xfip, current_ip = _fetch_season_xfip(current_season)
    prior_xfip, prior_ip = _fetch_season_xfip(prior_season)

    current_xfip = current_xfip or FALLBACK_FIP
    prior_xfip = prior_xfip or FALLBACK_FIP
    current_weight = 1.0 if current_ip >= MIN_RELIABLE_IP else (current_ip / MIN_RELIABLE_IP)
    prior_weight = 1.0 - current_weight

    bayesian_xfip = ((current_xfip * current_weight * current_ip) + (prior_xfip * prior_weight * prior_ip) + (FALLBACK_FIP * 20)) / ( (current_weight * current_ip) + (prior_weight * prior_ip) + 20 )
    return round(bayesian_xfip, 2)


def get_pitcher_siera(pitcher_name, sport_id=1, player_id=None):
    """Return a weighted multi-season SIERA for the named pitcher."""
    MIN_RELIABLE_IP = 20.0
    if pitcher_name in ('TBD', '', None): return FALLBACK_FIP
    if player_id is None:
        players = statsapi.lookup_player(pitcher_name, sportId=sport_id)
        if not players: return FALLBACK_FIP
        player_id = players[0]['id']
        
    current_season = max(SEASON_WEIGHTS.keys())
    prior_season   = current_season - 1

    def _fetch_season_siera(season):
        try:
            raw = statsapi.get('people', {'personIds': player_id, 'hydrate': f'stats(group=[pitching],type=season,season={season},sportId={sport_id})'})
            stats = {}
            for person in raw.get('people', []):
                for stat_grp in person.get('stats', []):
                    splits = stat_grp.get('splits', [])
                    if splits:
                        stats = splits[0].get('stat', {})
                        break
                if stats: break
            ip  = _parse_ip(stats.get('inningsPitched', '0'))
            siera = _calc_siera(stats)
            return siera, ip
        except Exception:
            return None, 0.0

    current_siera, current_ip = _fetch_season_siera(current_season)
    prior_siera, prior_ip = _fetch_season_siera(prior_season)

    current_siera = current_siera or FALLBACK_FIP
    prior_siera = prior_siera or FALLBACK_FIP
    current_weight = 1.0 if current_ip >= MIN_RELIABLE_IP else (current_ip / MIN_RELIABLE_IP)
    prior_weight = 1.0 - current_weight

    bayesian_siera = ((current_siera * current_weight * current_ip) + (prior_siera * prior_weight * prior_ip) + (FALLBACK_FIP * 20)) / ( (current_weight * current_ip) + (prior_weight * prior_ip) + 20 )
    return round(bayesian_siera, 2)
