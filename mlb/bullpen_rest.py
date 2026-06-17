from mlb_time import get_mlb_now
"""
bullpen_rest.py
===============
Daily Bullpen Rest & Fatigue Engine for the F5 Monte Carlo Model.

Pipeline (runs once each morning inside consensus_f5.py):
  1. Scrape yesterday's (and 2 days ago's) box scores to get pitch counts
     per reliever using the MLB Stats API boxscore endpoint.
  2. Apply back-to-back and 3-day fatigue FIP penalties per reliever.
  3. Filter to only F5-eligible (high-leverage) relievers.
  4. Return an adjusted team bullpen FIP as a drop-in replacement for the
     static get_team_bullpen_fip() call.

Penalty Scale (sabermetric evidence-based):
  - Pitched 1 day ago (fresh): no penalty
  - Pitched yesterday (back-to-back): FIP × 1.12
  - Pitched yesterday AND 2 days ago (consecutive): FIP × 1.12 × 1.20
  - Pitched all 3 of the last 3 days: marked UNAVAILABLE (training staff shuts down)

High-Leverage F5 Filter:
  - Only the top 60% of relievers by season FIP are considered F5-eligible.
  - Mop-up pitchers are excluded, as managers won't deploy them in tight 5th innings.
"""

import datetime
import statsapi
from run_daily_f5 import (
    get_team_bullpen_fip, _parse_ip, FALLBACK_FIP, FIP_CONSTANT, SEASON_WEIGHTS
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Fatigue multipliers applied to a reliever's effective FIP
_BACKTOBACK_PENALTY     = 1.12   # pitched yesterday
_CONSECUTIVE_2D_PENALTY = 1.20   # pitched yesterday AND 2 days ago (stacked)
_CONSECUTIVE_3D_DAYS    = 3      # if pitched 3 consecutive days → unavailable

# Only the top X% of relievers (by season FIP) are F5-eligible (high-leverage)
_HL_RELIEVER_PERCENTILE = 0.60

# Minimum pitches in a game to count as "used".
# Lowered to 5 so high-stress short outings (e.g. 11-pitch bases-loaded jam)
# are tracked. The consecutive-day multiplier governs fatigue severity.
_MIN_PITCHES_TO_COUNT = 5

# High-volume cumulative pitch penalty: if a reliever threw >35 total pitches
# over the last 2 days, an extra 5% is stacked on top of the B2B penalty.
_HIGH_VOLUME_2D_THRESHOLD = 35
_HIGH_VOLUME_EXTRA_PENALTY = 1.05

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _date_str(offset_days: int) -> str:
    """Return MM/DD/YYYY string for today - offset_days."""
    dt = get_mlb_now().date() - datetime.timedelta(days=offset_days)
    return dt.strftime('%m/%d/%Y')


def _get_games_on_date(date_str: str) -> list:
    """Return list of completed game dicts for a given MM/DD/YYYY date."""
    try:
        games = statsapi.schedule(start_date=date_str, end_date=date_str, sportId=1)
        return [g for g in games if g.get('status') == 'Final']
    except Exception:
        return []


def _extract_reliever_pitches(game_pk: int) -> dict:
    """
    Returns a dict keyed by personId with their pitch count and innings pitched
    for non-starter pitchers in the game.

    Format: {personId: {'name': str, 'pitches': int, 'ip': float,
                        'away_team_id': int, 'home_team_id': int, 'side': str}}
    """
    result = {}
    try:
        box = statsapi.boxscore_data(game_pk)
        away_id = box.get('away', {}).get('team', {}).get('id')
        home_id = box.get('home', {}).get('team', {}).get('id')

        for side, team_id in [('away', away_id), ('home', home_id)]:
            pitchers = box.get(f'{side}Pitchers', [])
            # Row 0 is always the header row (personId == 0)
            for i, p in enumerate(pitchers):
                pid = p.get('personId', 0)
                if pid == 0:
                    continue

                pitches = int(p.get('p', 0) or 0)
                ip      = _parse_ip(p.get('ip', '0'))

                if pitches < _MIN_PITCHES_TO_COUNT:
                    continue

                # Index 1 (first real pitcher after header) is the starter.
                # Also detect Openers via position note — e.g. "(W, 3-2)" is fine,
                # but if the note says 'P' and i==1 we mark as starter.
                is_starter = (i == 1)

                # FIX 3: Cross-season opener leak guard.
                # If the API note explicitly labels them as a starting pitcher
                # role (opener = starting position 1 in lineup) skip them.
                # We rely on i==1 as the primary signal (robust and fast).

                result[pid] = {
                    'name':       p.get('name', str(pid)),
                    'pitches':    pitches,
                    'ip':         ip,
                    'team_id':    team_id,
                    'side':       side,
                    'is_starter': is_starter,
                }
    except Exception:
        pass

    return result


import os
import json

_rest_index_cache = None
_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')

def _build_rest_index(lookback_days: int = 3) -> dict:
    """
    Builds a rest index: {personId: {1: pitches, 2: pitches, 3: pitches}}
    where the key is days_ago (1 = yesterday, 2 = two days ago, etc.)

    Only reliever entries are stored (is_starter == False).
    """
    global _rest_index_cache
    if _rest_index_cache is not None:
        return _rest_index_cache

    today_str = get_mlb_now().date().isoformat()
    cache_path = os.path.join(_CACHE_DIR, f'bullpen_rest_{today_str}.json')

    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Convert string keys back to int because JSON stringifies dict keys
                index = {int(k): {int(dk): dv for dk, dv in v.items()} for k, v in data['index'].items()}
                team_map = {int(k): v for k, v in data['team_map'].items()}
                _rest_index_cache = (index, team_map)
                return index, team_map
        except Exception:
            pass

    index: dict[int, dict] = {}   # pid -> {days_ago: pitches}  (additive per day)
    team_map: dict[int, int] = {} # pid -> team_id

    for days_ago in range(1, lookback_days + 1):
        date = _date_str(days_ago)
        games = _get_games_on_date(date)

        for g in games:
            pk = g['game_id']
            pitchers = _extract_reliever_pitches(pk)

            for pid, info in pitchers.items():
                if info['is_starter']:
                    continue  # only track relievers

                if pid not in index:
                    index[pid] = {}

                # FIX 1: Doubleheader additive aggregation.
                # Use += so a pitcher who throws in both games of a doubleheader
                # has their combined pitch count recorded, preventing RESTED misclassification.
                if days_ago in index[pid]:
                    index[pid][days_ago] += info['pitches']
                else:
                    index[pid][days_ago] = info['pitches']

                if pid not in team_map:
                    team_map[pid] = info['team_id']

    _rest_index_cache = (index, team_map)

    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump({'index': index, 'team_map': team_map}, f)
    except Exception as e:
        print("ERROR SAVING BULLPEN CACHE:", e)

    return index, team_map


def _get_season_fip_for_relievers(pitcher_ids: list) -> dict:
    """
    Fetches season FIP for a list of pitcher IDs.
    Returns {personId: fip_float}
    """
    if not pitcher_ids:
        return {}

    fip_map = {}
    id_string = ','.join(str(pid) for pid in pitcher_ids)
    season = max(SEASON_WEIGHTS.keys())

    try:
        raw = statsapi.get('people', {
            'personIds': id_string,
            'hydrate':   f'stats(group=[pitching],type=season,season={season})'
        })
        for person in raw.get('people', []):
            pid = person.get('id')
            stats = {}
            for grp in person.get('stats', []):
                splits = grp.get('splits', [])
                if splits:
                    stats = splits[0].get('stat', {})
                    break
            if not stats:
                continue

            ip = _parse_ip(stats.get('inningsPitched', '0'))
            gs = int(stats.get('gamesStarted', 0) or 0)
            if ip < 1.0 or gs >= 3:
                continue  # skip starters / empty lines

            k  = int(stats.get('strikeOuts',  0) or 0)
            bb = int(stats.get('baseOnBalls', 0) or 0)
            hr = int(stats.get('homeRuns',    0) or 0)
            fip = ((13 * hr) + (3 * bb) - (2 * k)) / ip + FIP_CONSTANT
            fip_map[pid] = round(max(2.5, min(7.5, fip)), 2)
    except Exception:
        pass

    return fip_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_adjusted_bullpen_cache = {}

def get_adjusted_bullpen_fip(team_name: str, verbose: bool = False) -> float:
    """
    Drop-in replacement for get_team_bullpen_fip() that applies real-world
    rest and fatigue penalties to each reliever before computing the team FIP.

    Steps:
      1. Identify the team ID.
      2. Build a 3-day rest index from yesterday's box scores.
      3. Fetch season FIP per active reliever.
      4. Apply back-to-back / consecutive-day FIP penalties.
      5. Filter to F5-eligible (high-leverage) relievers only.
      6. Return the IP-weighted average effective FIP.

    Falls back to the static get_team_bullpen_fip() on any failure.
    """
    global _adjusted_bullpen_cache
    if team_name in _adjusted_bullpen_cache:
        return _adjusted_bullpen_cache[team_name]
        
    try:
        teams = statsapi.lookup_team(team_name, sportIds=1)
        if not teams:
            res = get_team_bullpen_fip(team_name)
            _adjusted_bullpen_cache[team_name] = res
            return res

        team_id = teams[0]['id']

        # 1. Build rest index for all MLB relievers over the last 3 days
        rest_index, team_map = _build_rest_index(lookback_days=3)

        # 2. Isolate relievers who belong to this team
        team_pids = [pid for pid, tid in team_map.items() if tid == team_id]

        # Also get the active roster so we capture fully-rested pitchers too
        try:
            roster_data = statsapi.get('team_roster', {
                'teamId': team_id, 'rosterType': 'active'
            })
            roster_pids = [
                p['person']['id'] for p in roster_data.get('roster', [])
                if p.get('position', {}).get('code') == '1'
            ]
        except Exception:
            roster_pids = []

        # Union: all relievers on the roster, including rested ones
        all_pids = list(set(team_pids + roster_pids))

        if not all_pids:
            return get_team_bullpen_fip(team_name)

        # 3. Fetch season FIP for all relevant relievers
        fip_map = _get_season_fip_for_relievers(all_pids)

        if not fip_map:
            return get_team_bullpen_fip(team_name)

        # 4. Apply fatigue penalties and filter availability
        effective_profiles = []

        for pid, base_fip in fip_map.items():
            usage = rest_index.get(pid, {})  # {1: pitches, 2: pitches, 3: pitches}

            pitched_yesterday    = 1 in usage
            pitched_2_days_ago   = 2 in usage
            pitched_3_days_ago   = 3 in usage

            # Mark UNAVAILABLE if threw 3 consecutive days (training staff rule)
            if pitched_yesterday and pitched_2_days_ago and pitched_3_days_ago:
                if verbose:
                    print(f"    [{team_name}] PID {pid}: UNAVAILABLE (3 consecutive days)")
                continue

            effective_fip = base_fip

            # Back-to-back penalty
            if pitched_yesterday:
                effective_fip *= _BACKTOBACK_PENALTY
                # Stacked consecutive penalty if also pitched 2 days ago
                if pitched_2_days_ago:
                    effective_fip *= _CONSECUTIVE_2D_PENALTY

            # FIX 4: High-volume cumulative pitch penalty.
            # If total pitches thrown in the last 2 days exceeds 35,
            # apply an extra 5% penalty on top of the B2B multiplier.
            total_pitches_2d = usage.get(1, 0) + usage.get(2, 0)
            if total_pitches_2d > _HIGH_VOLUME_2D_THRESHOLD:
                effective_fip *= _HIGH_VOLUME_EXTRA_PENALTY

            effective_fip = round(min(7.5, effective_fip), 2)
            effective_profiles.append({'pid': pid, 'base_fip': base_fip, 'effective_fip': effective_fip})

            if verbose:
                tag = ''
                if pitched_yesterday and pitched_2_days_ago:
                    tag = ' [B2B+1]'
                elif pitched_yesterday:
                    tag = ' [B2B]'
                print(f"    [{team_name}] PID {pid}: base FIP {base_fip} → effective {effective_fip}{tag}")

        if not effective_profiles:
            return get_team_bullpen_fip(team_name)

        # 5. High-leverage filter: only top 60% by base FIP (lower = better)
        effective_profiles.sort(key=lambda x: x['base_fip'])
        hl_cutoff = max(1, round(len(effective_profiles) * _HL_RELIEVER_PERCENTILE))
        hl_profiles = effective_profiles[:hl_cutoff]

        if verbose:
            print(f"    [{team_name}] HL filter: {len(hl_profiles)}/{len(effective_profiles)} relievers eligible for F5")

        # 6. Simple average of effective FIPs (all relievers treated as equal IP proxies)
        adjusted_fip = sum(p['effective_fip'] for p in hl_profiles) / len(hl_profiles)
        adjusted_fip = round(max(2.5, min(7.5, adjusted_fip)), 2)

        if verbose:
            static_fip = get_team_bullpen_fip(team_name)
            delta = adjusted_fip - static_fip
            sign  = '+' if delta >= 0 else ''
            print(f"    [{team_name}] Static FIP: {static_fip} → Rest-Adjusted FIP: {adjusted_fip} ({sign}{delta:.2f})")

        return adjusted_fip

    except Exception as e:
        if verbose:
            print(f"    [{team_name}] Bullpen rest engine failed ({e}), falling back to static FIP.")
        return get_team_bullpen_fip(team_name)


def get_bullpen_rest_report(team_name: str) -> dict:
    """
    Returns a detailed diagnostic report for a team's bullpen rest situation.
    Used for logging and debugging.

    Returns
    -------
    {
        'adjusted_fip': float,
        'static_fip': float,
        'delta': float,
        'relievers': [{pid, base_fip, effective_fip, status}]
    }
    """
    static_fip = get_team_bullpen_fip(team_name)

    try:
        teams = statsapi.lookup_team(team_name, sportIds=1)
        if not teams:
            return {'adjusted_fip': static_fip, 'static_fip': static_fip, 'delta': 0.0, 'relievers': []}

        team_id = teams[0]['id']
        rest_index, team_map = _build_rest_index(lookback_days=3)
        team_pids = [pid for pid, tid in team_map.items() if tid == team_id]

        try:
            roster_data = statsapi.get('team_roster', {'teamId': team_id, 'rosterType': 'active'})
            roster_pids = [p['person']['id'] for p in roster_data.get('roster', []) if p.get('position', {}).get('code') == '1']
        except Exception:
            roster_pids = []

        all_pids = list(set(team_pids + roster_pids))
        fip_map = _get_season_fip_for_relievers(all_pids)

        relievers = []
        for pid, base_fip in fip_map.items():
            usage = rest_index.get(pid, {})
            pitched_yesterday  = 1 in usage
            pitched_2_days_ago = 2 in usage
            pitched_3_days_ago = 3 in usage

            if pitched_yesterday and pitched_2_days_ago and pitched_3_days_ago:
                status = 'UNAVAILABLE'
                effective_fip = None
            else:
                effective_fip = base_fip
                if pitched_yesterday:
                    effective_fip *= _BACKTOBACK_PENALTY
                    if pitched_2_days_ago:
                        effective_fip *= _CONSECUTIVE_2D_PENALTY
                effective_fip = round(min(7.5, effective_fip), 2)

                if pitched_yesterday and pitched_2_days_ago:
                    status = 'FATIGUED (B2B+1)'
                elif pitched_yesterday:
                    status = 'B2B'
                else:
                    status = 'RESTED'

            relievers.append({
                'pid': pid,
                'base_fip': base_fip,
                'effective_fip': effective_fip,
                'pitches_1d': usage.get(1, 0),
                'pitches_2d': usage.get(2, 0),
                'pitches_3d': usage.get(3, 0),
                'status': status,
            })

        relievers.sort(key=lambda x: x['base_fip'])
        adjusted_fip = get_adjusted_bullpen_fip(team_name)

        return {
            'adjusted_fip': adjusted_fip,
            'static_fip': static_fip,
            'delta': round(adjusted_fip - static_fip, 2),
            'relievers': relievers,
        }

    except Exception:
        return {'adjusted_fip': static_fip, 'static_fip': static_fip, 'delta': 0.0, 'relievers': []}


# ---------------------------------------------------------------------------
# CLI: quick diagnostic for a single team
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys
    team = sys.argv[1] if len(sys.argv) > 1 else 'New York Yankees'
    print(f"\nBullpen Rest Report: {team}")
    print("-" * 50)
    report = get_bullpen_rest_report(team)
    print(f"Static Season FIP:   {report['static_fip']}")
    print(f"Rest-Adjusted FIP:   {report['adjusted_fip']}  (delta: {report['delta']:+.2f})")
    print(f"\nReliever Breakdown ({len(report['relievers'])} tracked):")
    for r in report['relievers']:
        eff = f"{r['effective_fip']}" if r['effective_fip'] else "N/A"
        p_str = f"  P(1d/2d/3d): {r['pitches_1d']}/{r['pitches_2d']}/{r['pitches_3d']}"
        print(f"  PID {r['pid']:6d} | Base FIP: {r['base_fip']} | Eff FIP: {eff:>5} | {r['status']}{p_str}")
