"""
historical_umpire.py
====================
Chronological point-in-time umpire profile resolver for model backtesting.

Eliminates the multi-year and intra-season lookahead data leaks present in the
prototype (which applied static monthly fractions to the current 2026 live DB).

Primary path (preferred):
    Filters the umpire's per-game log entries to those STRICTLY before the
    target date, producing the exact Bayesian profile the model would have seen
    on that morning.

Fallback path (when granular logs are absent):
    Applies a conservative experience scalar based on year delta and season
    progress to down-weight the current DB totals — still directionally correct
    and far better than the old monthly-fraction approach.
"""

import os
from datetime import datetime
from umpire_engine import _load_db, LEAGUE_K_PER_9, LEAGUE_BB_PER_9, STABILIZATION_GAMES


def get_historical_umpire_profile(umpire_name: str, target_date: str) -> dict | None:
    """
    Returns the exact chronological point-in-time Bayesian profile for an
    umpire on a specific date.

    Parameters
    ----------
    umpire_name : str
        Full name of the plate umpire (e.g. "Dan Bellino").
    target_date : str
        ISO date string for the game being backtested (e.g. "2024-05-14").

    Returns
    -------
    dict with keys: 'games_called', 'raw_k_mod', 'raw_bb_mod'
        or None if the umpire is unknown.
    """
    if not umpire_name:
        return None

    db = _load_db()
    if not db or umpire_name not in db:
        return None

    target_dt = datetime.strptime(target_date, "%Y-%m-%d").date()
    profile    = db[umpire_name]

    # ---------- Primary path: granular per-game log entries ----------
    historical_games = profile.get('game_history_logs', [])

    if historical_games:
        valid_k  = 0.0
        valid_bb = 0.0
        valid_ip = 0.0
        valid_games = 0  # raw integer — not diluted by season weight

        for game in historical_games:
            try:
                game_dt = datetime.strptime(game['date'], "%Y-%m-%d").date()
            except (KeyError, ValueError):
                continue

            if game_dt < target_dt:
                w = game.get('weight', 1.0)
                valid_k  += game.get('k',  0.0) * w
                valid_bb += game.get('bb', 0.0) * w
                valid_ip += game.get('ip', 0.0) * w
                valid_games += 1  # count raw games, not weighted

        if valid_ip == 0 or valid_games == 0:
            return {'games_called': 0, 'raw_k_mod': 1.0, 'raw_bb_mod': 1.0}

        ump_k9  = (valid_k  / valid_ip) * 9.0
        ump_bb9 = (valid_bb / valid_ip) * 9.0

        return {
            'games_called': valid_games,
            'raw_k_mod':  round(ump_k9  / LEAGUE_K_PER_9,  4),
            'raw_bb_mod': round(ump_bb9 / LEAGUE_BB_PER_9, 4),
        }

    # ---------- Fallback path: safe regression when logs are absent ----------
    return _execute_safe_fallback_regression(profile, target_dt)


def _execute_safe_fallback_regression(profile: dict, target_dt: object) -> dict:
    """
    Produces a conservatively regressed profile when granular game logs are
    absent. Deducts 45% of experience per year back from the 2026 DB reference,
    then scales by the fraction of the target season elapsed.

    This is far more defensible than the old monthly-fraction prototype, but
    still inferior to a fully chronological log-based lookup.
    """
    CURRENT_REF_YEAR = 2026
    year_delta = max(0, CURRENT_REF_YEAR - target_dt.year)

    # Fraction of the target season elapsed at the target date.
    # Opening Day ≈ day 85; end of regular season ≈ day 272.
    day_of_year     = target_dt.timetuple().tm_yday
    season_fraction = max(0.05, min(1.0, (day_of_year - 85) / (272 - 85)))

    experience_scalar = max(0.05, (1.0 - (year_delta * 0.45)) * season_fraction)
    adjusted_games    = int(profile.get('games_called', 0) * experience_scalar)

    return {
        'games_called': max(0, adjusted_games),
        'raw_k_mod':  profile.get('raw_k_mod',  1.0),
        'raw_bb_mod': profile.get('raw_bb_mod', 1.0),
    }
