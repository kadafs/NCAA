from mlb_time import get_mlb_now
"""
umpire_engine.py
================
Umpire Strike-Zone Engine for the F5 Monte Carlo Model.

Pipeline:
  1. Morning scrape: update_umpire_db() fetches per-umpire stats from the
     MLB Stats API and writes them to data/umpires.json.
  2. Game-time lookup: get_umpire_for_game(game_pk) pulls today's plate
     umpire assignment from the live game feed.
  3. Modifier application: apply_umpire_sabermetric_layer() injects
     Bayesian-stabilized K% / BB% modifiers into a batter's raw rates
     BEFORE the fatigue and environmental engines run.

Modifiers are applied at the raw-talent input layer so that the existing
out_rate = 1.0 - total_non_out normalization loop absorbs them cleanly.
"""

import os
import json
import datetime
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

    # Season date ranges for regular season games
    season_dates = {
        2024: ('2024-03-20', '2024-09-29'),
        2025: ('2025-03-27', '2025-09-28'),
        2026: ('2026-03-26', '2026-09-27'),
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
                    agg[plate_ump] = {'k': 0.0, 'bb': 0.0, 'ip': 0.0, 'games': 0.0}

                agg[plate_ump]['k']     += total_k  * weight
                agg[plate_ump]['bb']    += total_bb * weight
                agg[plate_ump]['ip']    += total_ip * weight
                agg[plate_ump]['games'] += 1.0 * weight
                processed_pks.add(pk)

                if verbose and (i + 1) % 50 == 0:
                    print(f"    ... processed {i + 1}/{len(pks)} games")

            except Exception as e:
                if verbose and "Failed to resolve" not in str(e):
                    print(f"    Warning: boxscore fetch failed for game {pk}: {e}")
                continue

    # Convert accumulated stats to modifier ratios and merge into DB
    for name, stats in agg.items():
        if stats['ip'] == 0:
            continue
        ump_k9  = (stats['k']  / stats['ip']) * 9
        ump_bb9 = (stats['bb'] / stats['ip']) * 9

        existing = db.get(name, {})
        db[name] = {
            'games_called': round(stats['games'], 1),
            'raw_k_mod':    round(ump_k9  / LEAGUE_K_PER_9,  4),
            'raw_bb_mod':   round(ump_bb9 / LEAGUE_BB_PER_9, 4),
            'last_updated': today
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
    """
    if not umpire_name:
        return {'games_called': 0, 'raw_k_mod': 1.0, 'raw_bb_mod': 1.0}
    db = _load_db()
    return db.get(umpire_name, {'games_called': 0, 'raw_k_mod': 1.0, 'raw_bb_mod': 1.0})


# ---------------------------------------------------------------------------
# Core modifier: Bayesian-stabilized umpire K/BB layer
# ---------------------------------------------------------------------------
def apply_umpire_sabermetric_layer(
    base_rates: dict,
    umpire_profile: dict,
    stabilization_games: int = STABILIZATION_GAMES
) -> dict:
    """
    Applies Bayesian-stabilized umpire strike-zone modifiers to a batter's
    raw plate appearance input rates.

    Must be called BEFORE adjust_batter_rates() (pitcher/fatigue) and
    BEFORE apply_environmental_physics() so the existing out_rate normalization
    absorbs the adjustment cleanly.

    Parameters
    ----------
    base_rates        : Raw batter PA rate dict (keys: k, bb, hr, single, double, triple).
    umpire_profile    : Dict from load_umpire_profile(). Needs 'games_called',
                        'raw_k_mod', 'raw_bb_mod'.
    stabilization_games : Bayesian shrinkage threshold. Default 40 games.

    Returns
    -------
    Adjusted rate dict with stabilized k and bb values. All other keys unchanged.
    """
    # 1. Handle missing/unannounced umpires smoothly — return pristine rates
    if not umpire_profile or umpire_profile.get('games_called', 0) == 0:
        return base_rates

    games = umpire_profile['games_called']

    # 2. Bayesian Shrinkage: regress small sample sizes back to the league mean (1.0)
    # At games=40, weight=0.50 (equal credibility between data and prior).
    # At games=200, weight=0.83 (data dominates).
    weight = games / (games + stabilization_games)

    stabilized_k_mod  = (umpire_profile.get('raw_k_mod',  1.0) * weight) + (1.0 * (1.0 - weight))
    stabilized_bb_mod = (umpire_profile.get('raw_bb_mod', 1.0) * weight) + (1.0 * (1.0 - weight))

    # 3. Apply modifiers directly to the input rate dictionary
    adjusted = dict(base_rates)
    adjusted['k']  = adjusted.get('k',  0.22) * stabilized_k_mod
    adjusted['bb'] = adjusted.get('bb', 0.08) * stabilized_bb_mod

    # 4. Strict Bound Safeguards (prevent extreme out-of-bounds metrics)
    adjusted['k']  = max(0.05, min(0.45, adjusted['k']))
    adjusted['bb'] = max(0.02, min(0.20, adjusted['bb']))

    return adjusted


# ---------------------------------------------------------------------------
# CLI: run as a standalone morning scraper
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    print("Running umpire DB update...")
    update_umpire_db(verbose=True)
    print("Done.")
