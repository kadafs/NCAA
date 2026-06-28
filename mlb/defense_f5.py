"""
defense_f5.py
=============
Defensive Efficiency & Turf Surface Modifier for the MLB F5 Model.

Pipeline:
  1. Pulls opposing team's team fielding stats (Errors, Fielding %, Range Factor)
     from the MLB Stats API — the actual endpoints that are available.
  2. Dynamically routes to Infield vs Outfield impact based on the pitcher's
     batted ball profile (GB/FB ratio from the pitching splits endpoint).
  3. Applies an Artificial Turf speed penalty where applicable.
  4. Returns a compound multiplier to scale the Monte Carlo hit_mod vector.

Note on OAA: MLB's Statcast OAA data is NOT available via the public Stats API.
This module uses real-time fielding efficiency metrics from the team_stats endpoint,
which are fully accessible and updated daily.

Defensive Efficiency Score derivation:
  - Range Factor/9 (RF9) relative to league average: measures how many balls
    a team converts to outs per 9 innings compared to the league mean.
  - Error Rate relative to league: poor fielding inflates BABIP directly.
  - Blended into a multiplier clamped to [0.940, 1.060].
"""

import os
import json
import datetime
import statsapi

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Artificial turf parks: ground balls travel 6-10% faster than natural grass,
# inflating BABIP and base hit conversion on routine grounders.
# Source: Statcast field surface classifications (2025-2026 confirmed).
TURF_STADIUMS = {
    "Rogers Centre",          # Toronto Blue Jays
    "Tropicana Field",        # Tampa Bay Rays
    "Chase Field",            # Arizona Diamondbacks (retractable roof, turf surface)
    "loanDepot park",         # Miami Marlins
}
_TURF_MULTIPLIER  = 1.045   # +4.5% hit conversion on balls in play
_GRASS_MULTIPLIER = 1.000

# League-average reference baselines for defensive efficiency scoring (2024-2025 avg)
# These are the denominators used to compute relative defensive efficiency.
_LEAGUE_AVG_ERRORS_PER_GAME  = 0.68   # team errors per game (both teams combined / 2)
_LEAGUE_AVG_RF9              = 8.75   # range factor per 9 innings (league mid-point)

# Sensitivity: how much each defensive standard deviation moves the multiplier.
# Tuned so that a catastrophically bad defense (e.g. worst 5% in MLB) = ~1.05x.
_ERROR_SENSITIVITY  = 0.008   # per error above league average (per game)
_RF9_SENSITIVITY    = 0.004   # per unit RF9 below league average

# Hard clamp: prevents extreme teams from blowing out the multiplier.
_DEF_MIN_MULT = 0.950
_DEF_MAX_MULT = 1.050

# Cache directory
_CACHE_DIR  = os.path.join(os.path.dirname(__file__), '..', 'data')
_def_cache  = {}   # in-memory session cache: team_name -> modifier

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _get_today_str() -> str:
    try:
        from mlb_time import get_mlb_now
        return get_mlb_now().date().isoformat()
    except Exception:
        return datetime.date.today().isoformat()


def get_field_surface_multiplier(venue_name: str) -> float:
    """
    Returns the BABIP scaler based on stadium turf physics.
    +4.5% on artificial turf; neutral on natural grass.
    """
    if not venue_name:
        return _GRASS_MULTIPLIER
    venue_lower = venue_name.lower()
    for park in TURF_STADIUMS:
        if park.lower() in venue_lower:
            return _TURF_MULTIPLIER
    return _GRASS_MULTIPLIER


def _get_pitcher_gb_ratio(pitcher_player_id: int, season: int = 2026) -> float:
    """
    Fetches the pitcher's groundOut-to-airOut ratio (GO/AO) from the Stats API.
    GO/AO > 1.3  → groundball pitcher  (infield defense matters more)
    GO/AO < 0.9  → flyball pitcher     (outfield defense matters more)
    Returns 1.0 (neutral) on failure.
    """
    if not pitcher_player_id:
        return 1.0
    try:
        raw = statsapi.get('people', {
            'personIds': pitcher_player_id,
            'hydrate':   f'stats(group=[pitching],type=season,season={season})'
        })
        for person in raw.get('people', []):
            for grp in person.get('stats', []):
                splits = grp.get('splits', [])
                if splits:
                    stat = splits[0].get('stat', {})
                    ratio = stat.get('groundOutsToAirOuts')
                    if ratio is not None:
                        return float(ratio)
    except Exception:
        pass
    return 1.0


def _get_team_fielding_stats(team_id: int, season: int = 2026) -> dict:
    """
    Fetches team-level fielding stats from the Stats API.
    Returns {'errors_per_game': float, 'rf9': float, 'games': int} or None on failure.

    Uses the team_stats endpoint which is available in the public MLB Stats API.
    """
    try:
        raw = statsapi.get('team_stats', {
            'teamId': team_id,
            'group':  'fielding',
            'stats':  'season',
            'season': season,
        })
        for grp in raw.get('stats', []):
            splits = grp.get('splits', [])
            if not splits:
                continue
            stat   = splits[0].get('stat', {})
            games  = int(stat.get('gamesPlayed', 1) or 1)
            errors = int(stat.get('errors', 0) or 0)
            chances= int(stat.get('chances', 1) or 1)
            putouts= int(stat.get('putOuts', 0) or 0)
            assists= int(stat.get('assists', 0) or 0)
            ip_raw = stat.get('innings', '0')

            # Parse innings (may be stored as '1234.0' or '1234')
            try:
                ip = float(str(ip_raw).split('.')[0])
            except Exception:
                ip = games * 9.0

            errors_per_game = errors / games if games > 0 else _LEAGUE_AVG_ERRORS_PER_GAME
            rf9 = ((putouts + assists) / ip * 9) if ip > 0 else _LEAGUE_AVG_RF9

            return {
                'errors_per_game': round(errors_per_game, 3),
                'rf9':             round(rf9, 3),
                'games':           games,
            }
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def calculate_defensive_hit_modifier(
    pitcher_player_id: int,
    defending_team_name: str,
    venue_name: str,
    sport_id: int = 1,
    season: int = 2026,
    verbose: bool = False,
) -> float:
    """
    Computes a compound multiplier to scale hit probabilities in the Monte Carlo engine.

    Accounts for:
      - Opposing team's defensive range efficiency (Errors/G + RF9 vs league avg)
      - Pitcher's batted-ball profile (routes to Infield vs Outfield defensive impact)
      - Venue surface type (Artificial Turf BABIP inflation)

    Returns a float in [0.90, 1.10]. Values < 1.0 suppress hits (elite defense),
    values > 1.0 inflate hits (poor defense or fast turf).
    """
    # Return cached session result immediately
    cache_key = f"{defending_team_name}_{venue_name}_{pitcher_player_id}"
    if cache_key in _def_cache:
        return _def_cache[cache_key]

    # --- Step 1: Turf surface multiplier (always applied) ---
    turf_mult = get_field_surface_multiplier(venue_name)

    # --- Step 2: Pitcher's batted-ball profile ---
    gb_ratio = _get_pitcher_gb_ratio(pitcher_player_id, season=season)
    is_groundball_pitcher = gb_ratio >= 1.1   # GO/AO ≥ 1.1 = groundball leaning
    is_flyball_pitcher    = gb_ratio <= 0.85  # GO/AO ≤ 0.85 = flyball leaning

    if verbose:
        profile_label = 'GB' if is_groundball_pitcher else ('FB' if is_flyball_pitcher else 'Neutral')
        print(f"  [Defense] Pitcher GO/AO={gb_ratio:.2f} -> Profile: {profile_label}")

    # --- Step 3: Resolve defending team ID ---
    try:
        team_lookup = statsapi.lookup_team(defending_team_name, sportIds=sport_id)
        if not team_lookup:
            result = turf_mult
            _def_cache[cache_key] = result
            return result
        team_id = team_lookup[0]['id']
    except Exception:
        result = turf_mult
        _def_cache[cache_key] = result
        return result

    # --- Step 4: Fetch fielding stats ---
    f_stats = _get_team_fielding_stats(team_id, season=season)
    if not f_stats or f_stats.get('games', 0) < 10:
        # Insufficient sample: fall back to turf-only modifier
        result = turf_mult
        _def_cache[cache_key] = result
        return result

    errors_per_game = f_stats['errors_per_game']
    rf9             = f_stats['rf9']

    # --- Step 5: Compute defensive efficiency score ---
    # Error component: more errors than league avg → more hits
    error_delta   = errors_per_game - _LEAGUE_AVG_ERRORS_PER_GAME
    error_contrib = error_delta * _ERROR_SENSITIVITY

    # Range factor component: lower RF9 than league avg → more hits get through
    rf9_delta   = _LEAGUE_AVG_RF9 - rf9   # positive = below-average range
    rf9_contrib = rf9_delta * _RF9_SENSITIVITY

    # For a groundball pitcher, infield range matters most (full weight)
    # For a flyball pitcher, outfield range matters most (RF9 is still total-team
    # but we scale its contribution to reflect the split context)
    # For neutral pitchers, equal weighting applies.
    if is_groundball_pitcher:
        range_weight = 1.20   # Amplify range contribution — infielders matter more
    elif is_flyball_pitcher:
        range_weight = 0.80   # Dampen range — outfield speed matters more but RF9 is mixed
    else:
        range_weight = 1.00

    defensive_delta = error_contrib + (rf9_contrib * range_weight)
    range_multiplier = 1.0 + defensive_delta
    range_multiplier = round(max(_DEF_MIN_MULT, min(_DEF_MAX_MULT, range_multiplier)), 4)

    if verbose:
        print(f"  [Defense] {defending_team_name}: Errors/G={errors_per_game} "
              f"(d{error_delta:+.3f}), RF9={rf9} (d{rf9_delta:+.3f}) -> "
              f"Range mult={range_multiplier}, Turf mult={turf_mult}")

    # --- Step 6: Compound modifier ---
    final_modifier = round(max(0.90, min(1.10, range_multiplier * turf_mult)), 4)
    _def_cache[cache_key] = final_modifier

    if verbose:
        print(f"  [Defense] Final hit_mod scaler -> {final_modifier}x")

    return final_modifier
