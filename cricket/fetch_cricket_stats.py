"""
fetch_cricket_stats.py
======================
Hybrid data pipeline for cricket player statistics.

Architecture (Base + Delta):
  [Historical Baseline] Cricsheet.org local JSON dump
    - Career economy rate, wicket rate, boundary rate per player
    - Updated monthly from full data dump

  [Active In-Season Delta] CricketData.org API (free tier)
    - Recent scorecard data: runs, balls, wickets, economy per match
    - Pulled daily morning to capture form + injury replacements

  Profile blend: 0.65 x career_baseline + 0.35 x recent_delta
"""

import os
import sys
import json
import glob
import requests
from datetime import datetime, timedelta

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_CRICSHEET_DIR = os.path.join(_BASE_DIR, 'data', 'cricsheet')
_CACHE_DIR = os.path.join(_BASE_DIR, '..', 'data', 'cricket_cache')

# CricketData.org API config (free tier)
CRICKETDATA_API_KEY = os.environ.get('CRICKETDATA_API_KEY', '')
CRICKETDATA_BASE_URL = 'https://api.cricketdata.org'

os.makedirs(_CACHE_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# League Baseline Fallback Profiles
# ---------------------------------------------------------------------------
LEAGUE_BOWLER_BASELINE = {
    'economy_rate': 8.5,
    'wicket_rate': 0.045,
    'dot_rate': 0.370,
    'boundary_rate': 0.125,
    'wide_rate': 0.038,
}

LEAGUE_BATTER_BASELINE = {
    'boundary_pct': 0.148,
    'dot_pct': 0.380,
    'dismissal_rate': 0.048,
    'strike_rate': 132.0,
    'average': 24.0,
}

# Role tiers for position-based fallbacks
OPENER_BATTER = {**LEAGUE_BATTER_BASELINE, 'boundary_pct': 0.170, 'strike_rate': 138.0}
FINISHER_BATTER = {**LEAGUE_BATTER_BASELINE, 'boundary_pct': 0.200, 'strike_rate': 148.0, 'dot_pct': 0.330}
TAILENDER_BATTER = {**LEAGUE_BATTER_BASELINE, 'boundary_pct': 0.100, 'strike_rate': 110.0, 'dot_pct': 0.450, 'dismissal_rate': 0.090}

POWERPLAY_BOWLER = {**LEAGUE_BOWLER_BASELINE, 'economy_rate': 8.0, 'wicket_rate': 0.055}
DEATH_BOWLER = {**LEAGUE_BOWLER_BASELINE, 'economy_rate': 9.5, 'wicket_rate': 0.050, 'boundary_rate': 0.160}
SPINNER = {**LEAGUE_BOWLER_BASELINE, 'economy_rate': 7.8, 'wicket_rate': 0.042, 'dot_rate': 0.410}


# ---------------------------------------------------------------------------
# Step 1: Cricsheet JSON Parser (Historical Baseline)
# ---------------------------------------------------------------------------

def _load_cricsheet_index() -> dict:
    """
    Load and parse Cricsheet player register to map player names to IDs.
    Returns dict: {player_name_lower: player_id}
    """
    register_path = os.path.join(_CRICSHEET_DIR, 'people.csv')
    if not os.path.exists(register_path):
        return {}

    import csv
    index = {}
    with open(register_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get('name', '').strip().lower()
            pid = row.get('key_cricinfo', row.get('identifier', ''))
            if name and pid:
                index[name] = pid
    return index


def build_cricsheet_bowler_profile(player_name: str, formats: list = None) -> dict:
    """
    Parse local Cricsheet JSON files to build a bowler's career baseline.

    Cricsheet JSON structure per match:
      info.players / innings[].overs[].deliveries[]
        delivery: {bowler, batter, runs: {batter, extras, total},
                   wickets: [...], extras: {wides, noballs}}

    Parameters
    ----------
    player_name : Name as used in Cricsheet files
    formats     : List of format codes to include (e.g. ['T20', 'IT20'])
                  None = all formats

    Returns
    -------
    dict with bowler profile keys
    """
    cache_path = os.path.join(_CACHE_DIR, f'bowler_{player_name.replace(" ", "_").lower()}.json')
    if os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            if (datetime.now().timestamp() - mtime) < 86400 * 7:  # 7-day cache
                with open(cache_path, encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    name_lower = player_name.lower().strip()
    total_balls = 0
    total_wickets = 0
    total_runs_conceded = 0
    total_dots = 0
    total_boundaries = 0
    total_wides = 0
    total_noballs = 0

    json_files = glob.glob(os.path.join(_CRICSHEET_DIR, '**', '*.json'), recursive=True)

    for filepath in json_files:
        try:
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)

            # Filter by format
            match_format = data.get('info', {}).get('match_type', '').upper()
            if formats and match_format not in [fmt.upper() for fmt in formats]:
                continue

            innings_list = data.get('innings', [])
            for innings in innings_list:
                overs = innings.get('overs', [])
                for over_data in overs:
                    for delivery in over_data.get('deliveries', []):
                        bowler = delivery.get('bowler', '').lower().strip()
                        if bowler != name_lower:
                            continue

                        runs_data = delivery.get('runs', {})
                        batter_runs = runs_data.get('batter', 0)
                        extras_data = delivery.get('extras', {})
                        wides = extras_data.get('wides', 0)
                        noballs = extras_data.get('noballs', 0)

                        is_wide = wides > 0
                        is_noball = noballs > 0

                        if not is_wide:  # only legal deliveries count
                            total_balls += 1
                            total_runs_conceded += batter_runs
                            if batter_runs == 0 and not is_noball:
                                total_dots += 1
                            if batter_runs >= 4:
                                total_boundaries += 1

                        if is_wide:
                            total_wides += 1
                        if is_noball:
                            total_noballs += 1

                        wickets = delivery.get('wickets', [])
                        for w in wickets:
                            if w.get('kind', '') not in ('run out', 'obstructing the field'):
                                total_wickets += 1

        except Exception:
            continue

    if total_balls < 60:  # < 10 overs of data — insufficient
        return LEAGUE_BOWLER_BASELINE.copy()

    total_overs = total_balls / 6.0
    profile = {
        'economy_rate':  round(total_runs_conceded / total_overs, 2) if total_overs > 0 else 8.5,
        'wicket_rate':   round(total_wickets / total_balls, 4) if total_balls > 0 else 0.045,
        'dot_rate':      round(total_dots / total_balls, 4) if total_balls > 0 else 0.380,
        'boundary_rate': round(total_boundaries / total_balls, 4) if total_balls > 0 else 0.125,
        'wide_rate':     round(total_wides / (total_balls + total_wides) if (total_balls + total_wides) > 0 else 0.038, 4),
        'balls_parsed':  total_balls,
        'player_name':   player_name,
        'source':        'cricsheet',
    }

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

    return profile


def build_cricsheet_batter_profile(player_name: str, formats: list = None) -> dict:
    """
    Parse local Cricsheet JSON files to build a batter's career baseline.
    """
    cache_path = os.path.join(_CACHE_DIR, f'batter_{player_name.replace(" ", "_").lower()}.json')
    if os.path.exists(cache_path):
        try:
            mtime = os.path.getmtime(cache_path)
            if (datetime.now().timestamp() - mtime) < 86400 * 7:
                with open(cache_path, encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass

    name_lower = player_name.lower().strip()
    total_balls = 0
    total_runs = 0
    total_boundaries = 0
    total_dots = 0
    total_dismissals = 0

    json_files = glob.glob(os.path.join(_CRICSHEET_DIR, '**', '*.json'), recursive=True)

    for filepath in json_files:
        try:
            with open(filepath, encoding='utf-8') as f:
                data = json.load(f)

            match_format = data.get('info', {}).get('match_type', '').upper()
            if formats and match_format not in [fmt.upper() for fmt in formats]:
                continue

            innings_list = data.get('innings', [])
            for innings in innings_list:
                for over_data in innings.get('overs', []):
                    for delivery in over_data.get('deliveries', []):
                        batter = delivery.get('batter', '').lower().strip()
                        if batter != name_lower:
                            continue

                        extras = delivery.get('extras', {})
                        if extras.get('wides', 0) > 0:
                            continue  # wides don't count as balls faced

                        total_balls += 1
                        batter_runs = delivery.get('runs', {}).get('batter', 0)
                        total_runs += batter_runs

                        if batter_runs == 0:
                            total_dots += 1
                        if batter_runs >= 4:
                            total_boundaries += 1

                        wickets = delivery.get('wickets', [])
                        for w in wickets:
                            if w.get('player_out', '').lower().strip() == name_lower:
                                total_dismissals += 1

        except Exception:
            continue

    if total_balls < 60:
        return LEAGUE_BATTER_BASELINE.copy()

    profile = {
        'boundary_pct':   round(total_boundaries / total_balls, 4),
        'dot_pct':        round(total_dots / total_balls, 4),
        'dismissal_rate': round(total_dismissals / total_balls, 4),
        'strike_rate':    round((total_runs / total_balls) * 100, 1),
        'average':        round(total_runs / max(1, total_dismissals), 1),
        'balls_parsed':   total_balls,
        'player_name':    player_name,
        'source':         'cricsheet',
    }

    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(profile, f, indent=2)

    return profile


# ---------------------------------------------------------------------------
# Step 2: CricketData.org Live Delta
# ---------------------------------------------------------------------------

def fetch_live_scorecard_delta(player_name: str, last_n_matches: int = 5) -> list:
    """
    Fetch recent scorecard data from CricketData.org for a player.
    Returns list of match dicts with batting/bowling stats.
    Falls back to empty list if API key not configured.
    """
    if not CRICKETDATA_API_KEY:
        return []

    cache_path = os.path.join(_CACHE_DIR, f'delta_{player_name.replace(" ", "_").lower()}_{datetime.now().strftime("%Y-%m-%d")}.json')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    try:
        headers = {'apikey': CRICKETDATA_API_KEY}
        resp = requests.get(
            f'{CRICKETDATA_BASE_URL}/api/v1/player_stats',
            params={'name': player_name, 'format': 'T20'},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        recent = data.get('data', {}).get('recentMatches', [])[:last_n_matches]

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(recent, f, indent=2)
        return recent

    except Exception as e:
        print(f"[CricketData] Failed for {player_name}: {e}")
        return []


def fetch_today_playing_xi(match_id: str) -> dict:
    """
    Fetch the playing XI for a match from CricketData.org.
    Returns: {team1: [player_names], team2: [player_names]}
    """
    if not CRICKETDATA_API_KEY:
        return {}

    try:
        headers = {'apikey': CRICKETDATA_API_KEY}
        resp = requests.get(
            f'{CRICKETDATA_BASE_URL}/api/v1/match_squads',
            params={'match_id': match_id},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get('data', {})
    except Exception as e:
        print(f"[CricketData] Squad fetch failed for match {match_id}: {e}")
        return {}


def fetch_today_matches() -> list:
    """
    Fetch today's T20 match schedule from CricketData.org.
    Returns list of match dicts.
    """
    if not CRICKETDATA_API_KEY:
        print("[CricketData] No API key set. Set CRICKETDATA_API_KEY env variable.")
        return []

    today = datetime.now().strftime('%Y-%m-%d')
    cache_path = os.path.join(_CACHE_DIR, f'schedule_{today}.json')
    if os.path.exists(cache_path):
        try:
            with open(cache_path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass

    try:
        headers = {'apikey': CRICKETDATA_API_KEY}
        resp = requests.get(
            f'{CRICKETDATA_BASE_URL}/api/v1/matches',
            params={'date': today, 'type': 'T20'},
            headers=headers,
            timeout=10,
        )
        resp.raise_for_status()
        matches = resp.json().get('data', [])
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(matches, f, indent=2)
        return matches
    except Exception as e:
        print(f"[CricketData] Schedule fetch failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Step 3: Blended Profile Builder
# ---------------------------------------------------------------------------

def get_point_in_time_bowler_profile(player_name: str, formats: list = None) -> dict:
    """
    Blend historical Cricsheet baseline with recent CricketData.org delta.
    Weights: 65% career baseline + 35% recent form.

    Returns ready-to-use bowler profile dict for monte_carlo_t20.py
    """
    base = build_cricsheet_bowler_profile(player_name, formats=formats or ['T20', 'IT20'])
    delta = fetch_live_scorecard_delta(player_name)

    if not delta:
        return base

    # Aggregate bowling delta
    delta_balls = sum(float(d.get('bowling', {}).get('overs', 0)) * 6 for d in delta)
    delta_wickets = sum(int(d.get('bowling', {}).get('wickets', 0)) for d in delta)
    delta_runs = sum(int(d.get('bowling', {}).get('runs_conceded', 0)) for d in delta)
    delta_dots = sum(int(d.get('bowling', {}).get('dots', 0)) for d in delta)

    if delta_balls < 12:  # < 2 overs of recent data
        return base

    delta_overs = delta_balls / 6.0
    recent = {
        'economy_rate':  delta_runs / delta_overs if delta_overs > 0 else base['economy_rate'],
        'wicket_rate':   delta_wickets / delta_balls if delta_balls > 0 else base['wicket_rate'],
        'dot_rate':      delta_dots / delta_balls if delta_balls > 0 else base['dot_rate'],
        'boundary_rate': base['boundary_rate'],  # stable without detailed breakdown
        'wide_rate':     base['wide_rate'],
    }

    w_career, w_recent = 0.65, 0.35
    return {
        'economy_rate':  round(base['economy_rate']  * w_career + recent['economy_rate']  * w_recent, 2),
        'wicket_rate':   round(base['wicket_rate']   * w_career + recent['wicket_rate']   * w_recent, 4),
        'dot_rate':      round(base['dot_rate']      * w_career + recent['dot_rate']       * w_recent, 4),
        'boundary_rate': round(base['boundary_rate'], 4),
        'wide_rate':     round(base['wide_rate'],     4),
        'player_name':   player_name,
        'source':        'blended',
    }


def get_point_in_time_batter_profile(player_name: str, batting_position: int = 5,
                                      formats: list = None) -> dict:
    """
    Blend historical Cricsheet baseline with recent CricketData.org delta.
    Uses batting position to apply appropriate fallback tier.

    batting_position: 1-2 = opener, 3-6 = middle, 7-11 = tail
    """
    base = build_cricsheet_batter_profile(player_name, formats=formats or ['T20', 'IT20'])
    delta = fetch_live_scorecard_delta(player_name)

    if not delta:
        # Use position-based fallback if no Cricsheet data
        if base.get('balls_parsed', 0) < 60:
            if batting_position <= 2:
                return OPENER_BATTER.copy()
            elif batting_position >= 8:
                return TAILENDER_BATTER.copy()
            else:
                return LEAGUE_BATTER_BASELINE.copy()
        return base

    # Aggregate batting delta
    delta_balls = sum(int(d.get('batting', {}).get('balls_faced', 0)) for d in delta)
    delta_runs = sum(int(d.get('batting', {}).get('runs', 0)) for d in delta)
    delta_fours = sum(int(d.get('batting', {}).get('fours', 0)) for d in delta)
    delta_sixes = sum(int(d.get('batting', {}).get('sixes', 0)) for d in delta)
    delta_dismissals = sum(1 for d in delta if d.get('batting', {}).get('how_out', '') not in ('', 'not out', 'retired hurt'))

    if delta_balls < 15:
        return base

    delta_boundaries = delta_fours + delta_sixes
    recent = {
        'boundary_pct':   delta_boundaries / delta_balls if delta_balls > 0 else base['boundary_pct'],
        'dot_pct':        base['dot_pct'],  # hard to infer dots from scorecard summary
        'dismissal_rate': delta_dismissals / delta_balls if delta_balls > 0 else base['dismissal_rate'],
        'strike_rate':    (delta_runs / delta_balls * 100) if delta_balls > 0 else base['strike_rate'],
    }

    w_career, w_recent = 0.65, 0.35
    return {
        'boundary_pct':   round(base['boundary_pct']   * w_career + recent['boundary_pct']   * w_recent, 4),
        'dot_pct':        round(base['dot_pct'], 4),
        'dismissal_rate': round(base['dismissal_rate'] * w_career + recent['dismissal_rate'] * w_recent, 4),
        'strike_rate':    round(base['strike_rate']    * w_career + recent['strike_rate']    * w_recent, 1),
        'average':        base.get('average', 24.0),
        'player_name':    player_name,
        'source':         'blended',
    }
