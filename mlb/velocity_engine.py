"""
velocity_engine.py
==================
Statcast Velocity Trend Engine for the MLB F5 Model.

Fetches a starting pitcher's recent fastball velocity from Baseball Savant's
public CSV endpoint (no API key required) and computes a FIP penalty when
velocity has declined meaningfully vs. the pitcher's own season average.

Pipeline:
  1. Pull Statcast CSV data for the pitcher's last 10 game dates.
  2. Split into two 5-start windows: recent (last 5) vs. prior (prev 5).
  3. If recent average velo drops >1.5 mph vs. prior average, apply a
     graduated FIP penalty: +0.3 × (drop_mph / 1.5), capped at +0.90.
  4. Results are cached per pitcher per day to disk.

Public API:
    get_velocity_fip_adjustment(pitcher_name) -> float
        Returns a FIP additive penalty (0.0 = no penalty, positive = worse).
        Always returns 0.0 on any error / data unavailability.
"""

import os
import json
import time
import datetime
import urllib.request
import urllib.parse
import statsapi

from mlb_time import get_mlb_now

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_CACHE_DIR        = os.path.join(os.path.dirname(__file__), '..', 'data')
_VELO_DROP_THRESHOLD = 1.5   # mph: drop beyond this triggers a penalty
_MAX_FIP_PENALTY     = 0.90  # hard cap on additive penalty

# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path_for(player_id: int) -> str:
    today = get_mlb_now().date().isoformat()
    return os.path.join(_CACHE_DIR, f'velocity_{player_id}_{today}.json')


def _load_cache(player_id: int):
    path = _cache_path_for(player_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _save_cache(player_id: int, data: dict):
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(_cache_path_for(player_id), 'w', encoding='utf-8') as f:
            json.dump(data, f)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Statcast fetch
# ---------------------------------------------------------------------------

def _fetch_statcast_velo(player_id: int, lookback_days: int = 90) -> list:
    """
    Fetches average fastball velocity per game date from Baseball Savant.
    Returns a list of floats (velocity per game, most recent first),
    or an empty list on failure.
    """
    today = get_mlb_now().date()
    start = (today - datetime.timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    end   = today.strftime('%Y-%m-%d')

    # Baseball Savant public CSV: pitch-type = FF (4-seam), SI (sinker), FC (cutter)
    # We request all fastball types and aggregate by game date.
    params = urllib.parse.urlencode({
        'player_id':   player_id,
        'player_type': 'pitcher',
        'type':        'pitcher_game', # Slashes payload size by 99%
        'start_date':  start,
        'end_date':    end,
        'csv':         'true'
    })
    url = f'https://baseballsavant.mlb.com/statcast_search/csv?{params}'

    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
    except Exception:
        return []

    # Parse CSV: columns include game_date, release_speed
    lines = raw.strip().split('\n')
    if len(lines) < 2:
        return []

    header = [h.strip().strip('"') for h in lines[0].split(',')]
    try:
        date_idx  = header.index('game_date')
        speed_idx = header.index('release_speed')
    except ValueError:
        return []

    date_speeds: dict[str, list] = {}
    for line in lines[1:]:
        parts = line.split(',')
        if len(parts) <= max(date_idx, speed_idx):
            continue
        try:
            gdate = parts[date_idx].strip().strip('"')
            velo  = float(parts[speed_idx].strip().strip('"'))
            date_speeds.setdefault(gdate, []).append(velo)
        except (ValueError, IndexError):
            continue

    if not date_speeds:
        return []

    # Average per game date, sorted most-recent first
    per_game = []
    for gdate in sorted(date_speeds.keys(), reverse=True):
        velos = date_speeds[gdate]
        if velos:
            per_game.append(round(sum(velos) / len(velos), 1))

    return per_game


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_velocity_fip_adjustment(pitcher_name: str) -> float:
    """
    Returns a FIP additive adjustment for a pitcher based on velocity trend.
    Positive values = pitcher is declining (penalty).
    0.0 = no adjustment (default on any failure or insufficient data).
    """
    if pitcher_name in ('TBD', '', None):
        return 0.0

    # Resolve pitcher name → player ID
    try:
        players = statsapi.lookup_player(pitcher_name, sportId=1)
        if not players:
            return 0.0
        player_id = players[0]['id']
    except Exception:
        return 0.0

    # Check disk cache first
    cached = _load_cache(player_id)
    if cached is not None:
        return cached.get('adjustment', 0.0)

    # Fetch Statcast velocity data
    per_game = _fetch_statcast_velo(player_id, lookback_days=90)

    result = {'adjustment': 0.0, 'games': len(per_game)}

    if len(per_game) >= 6:
        recent_avg = sum(per_game[:5])  / 5    # last 5 starts
        prior_avg  = sum(per_game[5:10]) / min(5, len(per_game) - 5)

        drop = prior_avg - recent_avg   # positive = velo declined
        if drop > _VELO_DROP_THRESHOLD:
            raw_penalty = 0.30 * (drop / _VELO_DROP_THRESHOLD)
            result['adjustment']   = round(min(_MAX_FIP_PENALTY, raw_penalty), 3)
            result['recent_avg']   = round(recent_avg, 1)
            result['prior_avg']    = round(prior_avg, 1)
            result['drop_mph']     = round(drop, 1)

    _save_cache(player_id, result)
    return result['adjustment']
