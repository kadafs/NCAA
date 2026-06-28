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
  4. Return an IP-WEIGHTED adjusted team bullpen FIP as a drop-in replacement 
     for the static get_team_bullpen_fip() call.

 Sabermetric Corrections Implemented:
  - FIXED: Innings-Pitched Workload Weighting replaces flat arithmetic means.
  - FIXED: Non-overlapping conditional branches block high-volume double-penalties.
  - FIXED: Dynamic short-outing Opener checks protect bullpen day data tracking.
"""

import os
import json
import datetime
import statsapi
from run_daily_f5 import (
    get_team_bullpen_fip, _parse_ip, FALLBACK_FIP, FIP_CONSTANT, SEASON_WEIGHTS
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_BACKTOBACK_PENALTY     = 1.12   # pitched yesterday
_CONSECUTIVE_2D_PENALTY = 1.20   # pitched yesterday AND 2 days ago (stacked)
_CONSECUTIVE_3D_DAYS    = 3      # if pitched 3 consecutive days → unavailable

# Only the top X% of relievers (by season FIP) are F5-eligible (high-leverage)
_HL_RELIEVER_PERCENTILE = 0.60
_MIN_PITCHES_TO_COUNT = 5

# High-volume cumulative pitch threshold parameters
_HIGH_VOLUME_2D_THRESHOLD = 35
_HIGH_VOLUME_EXTRA_PENALTY = 1.05

# High-leverage availability thresholds
_HIGH_PITCH_SINGLE_GAME_THRESHOLD = 25
_HIGH_PITCH_UNAVAILABLE_PENALTY   = 1.15

_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
_rest_index_cache = None

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------
def _date_str(offset_days: int) -> str:
    dt = get_mlb_now().date() - datetime.timedelta(days=offset_days)
    return dt.strftime('%m/%d/%Y')


def _get_games_on_date(date_str: str) -> list:
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
                        'team_id': int, 'side': str, 'is_starter': bool}}
    """
    result = {}
    try:
        box = statsapi.boxscore_data(game_pk)
        away_id = box.get('away', {}).get('team', {}).get('id')
        home_id = box.get('home', {}).get('team', {}).get('id')

        for side, team_id in [('away', away_id), ('home', home_id)]:
            pitchers = box.get(f'{side}Pitchers', [])
            for i, p in enumerate(pitchers):
                pid = p.get('personId', 0)
                if pid == 0:
                    continue

                pitches = int(p.get('p', 0) or 0)
                ip      = _parse_ip(p.get('ip', '0'))

                if pitches < _MIN_PITCHES_TO_COUNT:
                    continue

                is_starter = (i == 1)

                # --- ADVANCED AUDIT FIX: DYNAMIC OPENER SHIELD ---
                # Re-classify 'starters' as relievers if they threw a short
                # bullpen-day opening assignment (<= 2.0 IP and < 35 pitches)
                if is_starter and ip <= 2.0 and pitches < 35:
                    is_starter = False

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


def _build_rest_index(lookback_days: int = 3) -> tuple[dict, dict]:
    """
    Builds a rest index: {personId: {1: pitches, 2: pitches, 3: pitches}}
    where the key is days_ago (1 = yesterday, 2 = two days ago, etc.)

    Only reliever entries are stored (is_starter == False).
    Returns (index, team_map).
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
                index = {int(k): {int(dk): dv for dk, dv in v.items()} for k, v in data['index'].items()}
                team_map = {int(k): v for k, v in data['team_map'].items()}
                _rest_index_cache = (index, team_map)
                return index, team_map
        except Exception:
            pass

    index = {}
    team_map = {}

    for days_ago in range(1, lookback_days + 1):
        date = _date_str(days_ago)
        games = _get_games_on_date(date)

        for g in games:
            pk = g['game_id']
            pitchers = _extract_reliever_pitches(pk)

            for pid, info in pitchers.items():
                if info['is_starter']:
                    continue

                if pid not in index:
                    index[pid] = {}

                # Doubleheader additive aggregation: use += so a pitcher who
                # throws in both games of a doubleheader has their combined
                # pitch count recorded, preventing RESTED misclassification.
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


def _get_season_fip_for_relievers_v6(pitcher_ids: list) -> dict:
    """
    V6 Ingestion Upgrade: Fetches season FIP metrics alongside total
    Innings Pitched (workload volume) to drive downstream IP weighting.

    Returns {personId: {'base_fip': float, 'season_ip': float}}
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
                continue  # Skip raw starters

            k  = int(stats.get('strikeOuts',  0) or 0)
            bb = int(stats.get('baseOnBalls', 0) or 0)
            hr = int(stats.get('homeRuns',    0) or 0)
            fip = ((13 * hr) + (3 * bb) - (2 * k)) / ip + FIP_CONSTANT

            # Map workload scale as an internal key alongside the rate stat
            fip_map[pid] = {
                'base_fip':  round(max(2.5, min(7.5, fip)), 2),
                'season_ip': ip
            }
    except Exception:
        pass

    return fip_map


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_adjusted_bullpen_cache = {}

def get_adjusted_bullpen_fip(team_name: str, verbose: bool = False) -> float:
    """
    V6 Rest Engine: Computes a mathematically precise, Innings-Pitched weighted
    average FIP for high-leverage bullpen profiles.

    Steps:
      1. Identify the team ID.
      2. Build a 3-day rest index from recent box scores.
      3. Fetch season FIP + season IP per active reliever.
      4. Apply mutually-exclusive fatigue penalties.
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
        rest_index, team_map = _build_rest_index(lookback_days=3)
        team_pids = [pid for pid, tid in team_map.items() if tid == team_id]

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

        all_pids = list(set(team_pids + roster_pids))
        if not all_pids:
            return get_team_bullpen_fip(team_name)

        # Draw structured multi-season volume dictionary map
        fip_map = _get_season_fip_for_relievers_v6(all_pids)
        if not fip_map:
            return get_team_bullpen_fip(team_name)

        effective_profiles = []

        for pid, profile in fip_map.items():
            base_fip  = profile['base_fip']
            season_ip = profile['season_ip']
            usage     = rest_index.get(pid, {})

            pitched_yesterday  = 1 in usage
            pitched_2_days_ago = 2 in usage
            pitched_3_days_ago = 3 in usage

            # Mark UNAVAILABLE if threw 3 consecutive days (training staff rule)
            if pitched_yesterday and pitched_2_days_ago and pitched_3_days_ago:
                if verbose:
                    print(f"    [{team_name}] PID {pid}: UNAVAILABLE (3 consecutive days)")
                continue

            effective_fip = base_fip
            yesterday_pitches = usage.get(1, 0)
            total_pitches_2d  = yesterday_pitches + usage.get(2, 0)

            # --- ADVANCED AUDIT FIX: ISOLATED MUTUAL EXCLUSION FILTER ---
            # Lock out overlapping single-game and multi-game fatigue scales.
            if yesterday_pitches > _HIGH_PITCH_SINGLE_GAME_THRESHOLD:
                # High single-game pitch load: pitcher is running on fumes.
                # Apply this penalty in isolation — B2B stacking is blocked.
                effective_fip *= _HIGH_PITCH_UNAVAILABLE_PENALTY
                if verbose:
                    print(f"    [{team_name}] PID {pid}: HIGH-PITCH LOCKOUT ({yesterday_pitches}p yesterday). Stacking blocked.")

            elif pitched_yesterday:
                # Pitcher didn't break the single-game threshold but did throw yesterday.
                effective_fip *= _BACKTOBACK_PENALTY

                if pitched_2_days_ago:
                    # Pitched yesterday AND two days ago (Consecutive)
                    effective_fip *= _CONSECUTIVE_2D_PENALTY

                    # Cumulative volume check only applies to multi-day workloads
                    if total_pitches_2d > _HIGH_VOLUME_2D_THRESHOLD:
                        effective_fip *= _HIGH_VOLUME_EXTRA_PENALTY
                        if verbose:
                            print(f"    [{team_name}] PID {pid}: Stacking Cumulative Volume (+5%) on top of Consecutive")

            # Hard safety ceiling cap to prevent mathematical overflow distortion
            effective_fip = round(min(7.5, effective_fip), 2)
            effective_profiles.append({
                'pid':          pid,
                'base_fip':     base_fip,
                'effective_fip': effective_fip,
                'ip':           season_ip
            })

            if verbose:
                tag = ''
                if pitched_yesterday and pitched_2_days_ago:
                    tag = ' [B2B+1]'
                elif pitched_yesterday:
                    tag = ' [B2B]'
                print(f"    [{team_name}] PID {pid}: base FIP {base_fip} → effective {effective_fip}{tag}")

        if not effective_profiles:
            return get_team_bullpen_fip(team_name)

        # 5. High-Leverage Selection Filter (Isolate Top 60% by Baseline Quality)
        effective_profiles.sort(key=lambda x: x['base_fip'])
        hl_cutoff = max(1, round(len(effective_profiles) * _HL_RELIEVER_PERCENTILE))
        hl_profiles = effective_profiles[:hl_cutoff]

        if verbose:
            print(f"    [{team_name}] HL filter: {len(hl_profiles)}/{len(effective_profiles)} relievers eligible for F5 workload calculations")

        # --- ADVANCED AUDIT FIX: INNINGS-PITCHED WEIGHTED AVERAGE ---
        # Replaces flat arithmetic means. Volume now dictates the baseline importance factor.
        total_hl_ip = sum(p['ip'] for p in hl_profiles)
        if total_hl_ip == 0:
            return get_team_bullpen_fip(team_name)

        weighted_fip_sum = sum(p['effective_fip'] * p['ip'] for p in hl_profiles)
        adjusted_fip = round(max(2.5, min(7.5, weighted_fip_sum / total_hl_ip)), 2)

        if verbose:
            static_fip = get_team_bullpen_fip(team_name)
            delta = adjusted_fip - static_fip
            sign  = '+' if delta >= 0 else ''
            print(f"    [{team_name}] Static Baseline: {static_fip} → Weighted Rest-Adjusted FIP: {adjusted_fip} ({sign}{delta:.2f})")

        _adjusted_bullpen_cache[team_name] = adjusted_fip
        return adjusted_fip

    except Exception as e:
        if verbose:
            print(f"    [{team_name}] Bullpen rest engine fatal exception ({e}), forcing static fallback.")
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
        'relievers': [{pid, base_fip, effective_fip, ip, status}]
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
            roster_pids = [
                p['person']['id'] for p in roster_data.get('roster', [])
                if p.get('position', {}).get('code') == '1'
            ]
        except Exception:
            roster_pids = []

        all_pids = list(set(team_pids + roster_pids))
        fip_map = _get_season_fip_for_relievers_v6(all_pids)

        relievers = []
        for pid, profile in fip_map.items():
            base_fip  = profile['base_fip']
            season_ip = profile['season_ip']
            usage = rest_index.get(pid, {})

            pitched_yesterday  = 1 in usage
            pitched_2_days_ago = 2 in usage
            pitched_3_days_ago = 3 in usage

            if pitched_yesterday and pitched_2_days_ago and pitched_3_days_ago:
                status = 'UNAVAILABLE'
                effective_fip = None
            else:
                effective_fip     = base_fip
                yesterday_pitches = usage.get(1, 0)
                total_pitches_2d  = yesterday_pitches + usage.get(2, 0)

                if yesterday_pitches > _HIGH_PITCH_SINGLE_GAME_THRESHOLD:
                    effective_fip *= _HIGH_PITCH_UNAVAILABLE_PENALTY
                    status = f'HIGH-PITCH LOCKOUT ({yesterday_pitches}p)'
                elif pitched_yesterday:
                    effective_fip *= _BACKTOBACK_PENALTY
                    if pitched_2_days_ago:
                        effective_fip *= _CONSECUTIVE_2D_PENALTY
                        if total_pitches_2d > _HIGH_VOLUME_2D_THRESHOLD:
                            effective_fip *= _HIGH_VOLUME_EXTRA_PENALTY
                        status = 'FATIGUED (B2B+1)'
                    else:
                        status = 'B2B'
                else:
                    status = 'RESTED'

                effective_fip = round(min(7.5, effective_fip), 2)

            relievers.append({
                'pid':          pid,
                'base_fip':     base_fip,
                'effective_fip': effective_fip,
                'ip':           season_ip,
                'pitches_1d':   usage.get(1, 0),
                'pitches_2d':   usage.get(2, 0),
                'pitches_3d':   usage.get(3, 0),
                'status':       status,
            })

        relievers.sort(key=lambda x: x['base_fip'])
        adjusted_fip = get_adjusted_bullpen_fip(team_name)

        return {
            'adjusted_fip': adjusted_fip,
            'static_fip':   static_fip,
            'delta':        round(adjusted_fip - static_fip, 2),
            'relievers':    relievers,
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
        eff   = f"{r['effective_fip']}" if r['effective_fip'] is not None else "N/A"
        ip    = f"{r['ip']:.1f}IP"
        p_str = f"  P(1d/2d/3d): {r['pitches_1d']}/{r['pitches_2d']}/{r['pitches_3d']}"
        print(f"  PID {r['pid']:6d} | Base FIP: {r['base_fip']} | Eff FIP: {eff:>5} | {ip} | {r['status']}{p_str}")
