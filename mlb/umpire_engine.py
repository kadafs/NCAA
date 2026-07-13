from mlb_time import get_mlb_now
"""
umpire_engine.py
================
Umpire Strike-Zone Engine for the F5 Monte Carlo Model.

Pipeline:
  1. Morning scrape: update_umpire_db() fetches per-umpire stats from the
     MLB Stats API (sport 1) AND MiLB (sports 11, 12), writing combined
     profiles to data/umpires.json.
  2. Game-time lookup: get_umpire_for_game(game_pk) pulls today's plate
     umpire assignment from the live game feed (works for all sports).
  3. Modifier application: apply_umpire_sabermetric_layer() injects
     Bayesian-stabilized K% / BB% modifiers into a batter's raw rates
     BEFORE the fatigue and environmental engines run.

Rotating umpires who work both MLB and MiLB accumulate games across all
levels, giving them stronger Bayesian profiles.  Dedicated MiLB umpires
are profiled from minor-league data only.  Modifiers are applied at the
raw-talent input layer so that the normalization loop absorbs them cleanly.
"""

import os
import json
import datetime
from datetime import date as _date, timedelta as _td
import statsapi

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# League-average reference baselines (2022-2025 rolling average)
LEAGUE_K_PER_9  = 8.8
LEAGUE_BB_PER_9 = 3.1

# Path to the local umpire database
_DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'umpires.json')

# Bayesian shrinkage stabilization threshold (in games called).
# An umpire with 40 games has roughly equal weight to the league mean and their own data.
STABILIZATION_GAMES = 40

# Rolling window: how many seasons back to blend
_SEASONS = [2024, 2025, 2026]
_SEASON_WEIGHTS = {2024: 0.20, 2025: 0.30, 2026: 0.50}


# ---------------------------------------------------------------------------
# Local DB Helpers
# ---------------------------------------------------------------------------
def _load_db() -> dict:
    """Load the local umpires.json database. Returns empty dict on missing file."""
    if not os.path.exists(_DB_PATH):
        return {}
    try:
        with open(_DB_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}


def _save_db(db: dict) -> None:
    """Persist the umpire database to disk."""
    os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
    with open(_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=2)


# ---------------------------------------------------------------------------
# Scraper: build / refresh umpire stats from the MLB Stats API
# ---------------------------------------------------------------------------
def _parse_ip(ip_str: str) -> float:
    """Convert '6.1' (6 1/3 innings) format to a float."""
    parts = str(ip_str).split('.')
    return float(parts[0]) + (float(parts[1]) / 3.0 if len(parts) > 1 and parts[1] else 0.0)


def update_umpire_db(verbose: bool = False) -> None:
    """
    Fetches per-umpire K9 / BB9 deviation stats from the MLB Stats API
    and merges them into data/umpires.json.

    Uses statsapi.schedule() (no fields filter) so game status is intact,
    then pulls the boxscore per game for umpire + K/BB data.
    Full 3-season bootstrap takes ~5-10 min due to API rate limits.
    Weekly incremental runs are fast (7 new games).
    """
    db = _load_db()
    today = get_mlb_now().date().isoformat()

    # Track which game_pks we've already processed to avoid re-fetching
    processed_pks = set(db.get('_processed_pks', []))

    # Accumulate weighted K/BB counts per umpire name
    # Initialize the aggregation pool from existing database values to prevent baseline overwrite
    agg: dict[str, dict] = {}
    for name, data in db.items():
        if name.startswith('_'):
            continue
        # Reverse-engineer raw volumes from historical rates to allow additive math
        historical_games = data.get('games_called', 0.0)
        historical_ip = historical_games * 9.0 * 2.0  # Safe proxy: 18 innings per game called
        agg[name] = {
            'k': (data.get('raw_k_mod', 1.0) * LEAGUE_K_PER_9 / 9.0) * historical_ip,
            'bb': (data.get('raw_bb_mod', 1.0) * LEAGUE_BB_PER_9 / 9.0) * historical_ip,
            'ip': historical_ip,
            'games': historical_games
        }

    # Season date ranges — MLB
    season_dates = {
        2024: ('2024-03-20', '2024-09-29'),
        2025: ('2025-03-27', '2025-09-28'),
        2026: ('2026-03-26', '2026-09-27'),
    }

    # Season date ranges — MiLB (AAA=11, AA=12 share same calendar)
    milb_season_dates = {
        2024: ('2024-04-05', '2024-09-22'),
        2025: ('2025-04-04', '2025-09-21'),
        2026: ('2026-04-01', '2026-09-21'),
    }

    for season, weight in _SEASON_WEIGHTS.items():
        start_dt, end_dt = season_dates[season]
        if verbose:
            print(f"  Fetching schedule for {season} ({start_dt} to {end_dt})...")

        try:
            # statsapi.schedule() is the high-level wrapper — no fields filter,
            # so status.abstractGameState is fully populated.
            raw_schedule = statsapi.schedule(
                start_date=start_dt,
                end_date=end_dt,
                sportId=1
            )
        except Exception as e:
            if verbose:
                print(f"    Warning: schedule fetch failed for {season}: {e}")
            continue

        # Filter to Final games we haven't processed yet
        pks = [
            g['game_id'] for g in raw_schedule
            if g.get('status') == 'Final' and g['game_id'] not in processed_pks
        ]

        if verbose:
            print(f"    Found {len(pks)} new completed games in {season}.")

        # Build a game_pk → date mapping so we can stamp each log entry.
        pk_to_date = {g['game_id']: g.get('game_date', '') for g in raw_schedule}

        for i, pk in enumerate(pks):
            try:
                # game_boxScore is a lightweight endpoint (no play-by-play)
                box = statsapi.boxscore_data(pk)
                
                # --- Plate umpire ---
                plate_ump = None
                # gameBoxInfo is a list of dicts: [{'label': 'Umpires', 'value': 'HP: Dan Bellino. 1B: Phil Cuzzi...'}, ...]
                for item in box.get('gameBoxInfo', []):
                    if isinstance(item, dict) and item.get('label') == 'Umpires':
                        ump_str = item.get('value', '')
                        if 'HP: ' in ump_str:
                            plate_ump = ump_str.split('HP: ')[1].split('.')[0].strip()
                        break
                        
                # Fallback: officials can also be at top level if the API structure shifts
                if not plate_ump:
                    for o in box.get('officials', []):
                        if isinstance(o, dict) and o.get('officialType') == 'Home Plate':
                            plate_ump = o.get('official', {}).get('fullName')
                            break

                if not plate_ump:
                    processed_pks.add(pk)
                    continue

                # --- K / BB / IP from both team pitching lines ---
                total_k = total_bb = total_ip = 0.0
                for side in ('away', 'home'):
                    pitching = box.get(side + 'PitchingTotals', {})
                    total_k  += float(pitching.get('k',  0) or 0)
                    total_bb += float(pitching.get('bb', 0) or 0)
                    total_ip += _parse_ip(pitching.get('ip', '0'))

                if total_ip < 4:
                    processed_pks.add(pk)
                    continue

                if plate_ump not in agg:
                    agg[plate_ump] = {'k': 0.0, 'bb': 0.0, 'ip': 0.0, 'games': 0}

                agg[plate_ump]['k']     += total_k  * weight
                agg[plate_ump]['bb']    += total_bb * weight
                agg[plate_ump]['ip']    += total_ip * weight
                # FIX (2026-06-30): Track raw game count as integer.
                # Previous code used `+= 1.0 * weight`, which diluted the
                # Bayesian shrinkage denominator and over-regressed experienced
                # umpires toward the league mean.
                agg[plate_ump]['games'] += 1

                # --- Append chronological game log for point-in-time backtest lookups ---
                game_date_str = pk_to_date.get(pk, '')
                if plate_ump not in db:
                    db[plate_ump] = {}
                if 'game_history_logs' not in db[plate_ump]:
                    db[plate_ump]['game_history_logs'] = []
                db[plate_ump]['game_history_logs'].append({
                    'date': game_date_str,
                    'k':    total_k,
                    'bb':   total_bb,
                    'ip':   total_ip,
                    'weight': weight,
                })

                processed_pks.add(pk)

                if verbose and (i + 1) % 50 == 0:
                    print(f"    ... processed {i + 1}/{len(pks)} games")

            except Exception as e:
                if verbose and "Failed to resolve" not in str(e):
                    print(f"    Warning: boxscore fetch failed for game {pk}: {e}")
                continue

    # ── MiLB scraping (AAA=11, AA=12) ────────────────────────────────────────
    # Uses raw statsapi.get() since the high-level schedule() wrapper is MLB-only.
    # Rotating umpires accumulate across MLB + MiLB in the same agg dict.
    for milb_sport_id, milb_label in ((11, 'AAA'), (12, 'AA')):
        for season, weight in _SEASON_WEIGHTS.items():
            start_dt, end_dt_s = milb_season_dates[season]
            if verbose:
                print(f"  Fetching {milb_label} schedule for {season} ({start_dt} to {end_dt_s})...")

            try:
                current   = _date.fromisoformat(start_dt)
                end_date  = min(_date.fromisoformat(end_dt_s), _date.today())
                milb_pks  = []

                # Weekly batches to stay within API rate limits
                while current <= end_date:
                    window_end = min(current + _td(days=6), end_date)
                    data = statsapi.get('schedule', {
                        'sportId':   milb_sport_id,
                        'startDate': current.strftime('%Y-%m-%d'),
                        'endDate':   window_end.strftime('%Y-%m-%d'),
                    })
                    for date_obj in data.get('dates', []):
                        for g in date_obj.get('games', []):
                            state = g.get('status', {}).get('abstractGameState')
                            gpk   = g.get('gamePk')
                            if state == 'Final' and gpk and gpk not in processed_pks:
                                milb_pks.append(gpk)
                                pk_to_date[gpk] = date_obj.get('date', '')
                    current = window_end + _td(days=1)

            except Exception as e:
                if verbose:
                    print(f"    Warning: {milb_label} schedule fetch failed for {season}: {e}")
                continue

            if verbose:
                print(f"    Found {len(milb_pks)} new completed {milb_label} games in {season}.")

            for i, pk in enumerate(milb_pks):
                try:
                    box = statsapi.boxscore_data(pk)

                    # --- Plate umpire (officials list is populated for MiLB) ---
                    plate_ump = None
                    for o in box.get('officials', []):
                        if isinstance(o, dict) and o.get('officialType') == 'Home Plate':
                            plate_ump = o.get('official', {}).get('fullName')
                            break
                    # Fallback: gameBoxInfo text (MLB format, may appear in some MiLB boxscores)
                    if not plate_ump:
                        for item in box.get('gameBoxInfo', []):
                            if isinstance(item, dict) and item.get('label') == 'Umpires':
                                ump_str = item.get('value', '')
                                if 'HP: ' in ump_str:
                                    plate_ump = ump_str.split('HP: ')[1].split('.')[0].strip()
                                break

                    if not plate_ump:
                        processed_pks.add(pk)
                        continue

                    # --- K / BB / IP from both pitching lines ---
                    total_k = total_bb = total_ip = 0.0
                    for side in ('away', 'home'):
                        pitching  = box.get(side + 'PitchingTotals', {})
                        total_k  += float(pitching.get('k',  0) or 0)
                        total_bb += float(pitching.get('bb', 0) or 0)
                        total_ip += _parse_ip(pitching.get('ip', '0'))

                    if total_ip < 4:
                        processed_pks.add(pk)
                        continue

                    if plate_ump not in agg:
                        agg[plate_ump] = {'k': 0.0, 'bb': 0.0, 'ip': 0.0, 'games': 0}

                    agg[plate_ump]['k']     += total_k  * weight
                    agg[plate_ump]['bb']    += total_bb * weight
                    agg[plate_ump]['ip']    += total_ip * weight
                    agg[plate_ump]['games'] += 1

                    game_date_str = pk_to_date.get(pk, '')
                    if plate_ump not in db:
                        db[plate_ump] = {}
                    if 'game_history_logs' not in db[plate_ump]:
                        db[plate_ump]['game_history_logs'] = []
                    db[plate_ump]['game_history_logs'].append({
                        'date':   game_date_str,
                        'sport':  milb_label,
                        'k':      total_k,
                        'bb':     total_bb,
                        'ip':     total_ip,
                        'weight': weight,
                    })

                    processed_pks.add(pk)

                    if verbose and (i + 1) % 100 == 0:
                        print(f"    ... processed {i + 1}/{len(milb_pks)} {milb_label} games")

                except Exception as e:
                    if verbose and 'Failed to resolve' not in str(e):
                        print(f"    Warning: {milb_label} boxscore {pk}: {e}")
                    continue

    # Convert accumulated stats to modifier ratios and merge into DB.
    # Preserve game_history_logs written during the inner loop above.
    for name, stats in agg.items():
        if stats['ip'] == 0:
            continue
        ump_k9  = (stats['k']  / stats['ip']) * 9
        ump_bb9 = (stats['bb'] / stats['ip']) * 9

        existing = db.get(name, {})
        db[name] = {
            # FIX (2026-06-30): Store raw integer game count so Bayesian
            # shrinkage weight = games / (games + 40) uses real experience.
            'games_called': int(stats['games']),
            'raw_k_mod':    round(ump_k9  / LEAGUE_K_PER_9,  4),
            'raw_bb_mod':   round(ump_bb9 / LEAGUE_BB_PER_9, 4),
            'last_updated': today,
            # Preserve chronological log entries written during the scrape loop.
            'game_history_logs': existing.get('game_history_logs', []),
        }

    # Persist the processed PKs index so weekly re-runs skip old games
    db['_processed_pks'] = list(processed_pks)
    _save_db(db)

    umpire_count = sum(1 for k in db if not k.startswith('_'))
    if verbose:
        print(f"  Umpire DB updated: {umpire_count} umpires saved to {_DB_PATH}")



# ---------------------------------------------------------------------------
# Game-time: resolve today's plate umpire for a given game_pk
# ---------------------------------------------------------------------------
def get_umpire_for_game(game_pk: int) -> str | None:
    """
    Fetches the plate umpire name for a given game_pk from the MLB live feed.
    Returns None if the umpire assignment hasn't been released yet (~2 hrs before first pitch).
    """
    try:
        feed = statsapi.get('game', {
            'gamePk': game_pk,
            'fields': 'liveData,boxscore,officials,official,fullName'
        })
        officials = feed.get('liveData', {}).get('boxscore', {}).get('officials', [])
        for o in officials:
            if o.get('officialType') == 'Home Plate':
                return o['official']['fullName']
    except Exception:
        pass
    return None


def load_umpire_profile(umpire_name: str | None) -> dict:
    """
    Loads a single umpire's profile dict from the local DB.
    Returns a neutral profile if umpire is unknown or DB is missing.

    Tries multiple name-matching strategies in order:
      1. Exact match
      2. Case-insensitive match
      3. Last-name-only match (handles "B. Walsh" vs "Brian Walsh")
    """
    _NEUTRAL = {'games_called': 0, 'raw_k_mod': 1.0, 'raw_bb_mod': 1.0}
    if not umpire_name:
        return _NEUTRAL
    db = _load_db()

    # 1. Exact match
    if umpire_name in db:
        return db[umpire_name]

    # 2. Case-insensitive match
    name_lower = umpire_name.lower()
    for key, val in db.items():
        if key.lower() == name_lower:
            return val

    # 3. Last-name-only fallback (handles "B. Walsh" → "Brian Walsh")
    last_name = umpire_name.strip().split()[-1].lower()
    candidates = [(k, v) for k, v in db.items()
                  if k.strip().split()[-1].lower() == last_name]
    if len(candidates) == 1:
        return candidates[0][1]

    return _NEUTRAL


# ---------------------------------------------------------------------------
# Core modifier: Bayesian-stabilized umpire K/BB layer
# ---------------------------------------------------------------------------
def apply_umpire_sabermetric_layer(
    base_rates: dict,
    umpire_profile: dict,
    stabilization_games: int = STABILIZATION_GAMES
) -> dict:
    """
    Calculates Bayesian-stabilized umpire modifiers and stores them as
    passthrough keys ('ump_k_mod', 'ump_bb_mod') in the returned dict.

    FIX (2026-06-30): The previous implementation scaled 'k' and 'bb' directly
    on the batter's raw input rates. Because all hit types are proportional to
    prob_bip = 1 - (prob_k + prob_bb), an elite strike-zone umpire accidentally
    suppressed singles, doubles, triples, and home runs equally — the "Out-Rate
    Erasure" bug. The fix stores multipliers as neutral passthrough keys so that
    adjust_batter_rates() can apply them strictly to prob_k and prob_bb AFTER
    the log-odds blend, leaving the batted-ball distribution intact.

    Parameters
    ----------
    base_rates        : Raw batter PA rate dict (keys: k, bb, hr, single, …).
    umpire_profile    : Dict from load_umpire_profile(). Needs 'games_called',
                        'raw_k_mod', 'raw_bb_mod'.
    stabilization_games : Bayesian shrinkage threshold. Default 40 games.

    Returns
    -------
    Dict with all original keys plus 'ump_k_mod' and 'ump_bb_mod'.
    When no umpire data exists both keys default to 1.0 (no effect).
    """
    adjusted = dict(base_rates)
    # Always inject defaults so adjust_batter_rates() can read them unconditionally.
    adjusted['ump_k_mod']  = 1.0
    adjusted['ump_bb_mod'] = 1.0

    if not umpire_profile or umpire_profile.get('games_called', 0) == 0:
        return adjusted

    games = umpire_profile['games_called']

    # Bayesian Shrinkage: regress small sample sizes back to the league mean (1.0).
    # At games=40, weight=0.50 (equal credibility between data and prior).
    # At games=200, weight=0.83 (data dominates).
    weight = games / (games + stabilization_games)

    stabilized_k_mod  = (umpire_profile.get('raw_k_mod',  1.0) * weight) + (1.0 * (1.0 - weight))
    stabilized_bb_mod = (umpire_profile.get('raw_bb_mod', 1.0) * weight) + (1.0 * (1.0 - weight))

    # Strict boundary safeguards.
    adjusted['ump_k_mod']  = max(0.80, min(1.20, stabilized_k_mod))
    adjusted['ump_bb_mod'] = max(0.75, min(1.25, stabilized_bb_mod))

    return adjusted


# ---------------------------------------------------------------------------
# CLI: run as a standalone morning scraper
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("Running umpire DB update...")
    update_umpire_db(verbose=True)
    print("Done.")
