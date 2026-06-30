"""
full_game_model.py
==================
Full Game (9-inning) Monte Carlo Simulation Engine.

Extends the F5 Monte Carlo model (monte_carlo_f5.py) through innings 6-9
by simulating the late-inning environment with the team's rest-adjusted bullpen.

Architecture:
  Full Game = F5 Innings (1-5)  +  Late Innings (6-9)

  Late innings use:
    - get_adjusted_bullpen_fip()   from bullpen_rest.py  (fatigue-adjusted)
    - fip_to_bullpen_pa_rates()    (converts FIP to per-PA rates for MC)
    - simulate_half_inning_vectorized()  from monte_carlo_f5.py (reused)
    - The same confirmed lineup (batting order carries over from F5)
    - No TTTO penalty for relievers (relievers face batters 1x each)

Public API:
    run_full_game_mc(
        away_lineup_ids, home_lineup_ids,
        away_pitcher_name, home_pitcher_name,
        away_pitcher_fip, home_pitcher_fip,
        away_team_name, home_team_name,
        **kwargs  (same as run_monte_carlo_f5)
    ) -> dict

Returns:
    {
        'f5_total':         float,   # MC F5 total (innings 1-5)
        'late_total':       float,   # MC Late total (innings 6-9)
        'full_game_total':  float,   # F5 + Late
        'away_full_runs':   float,
        'home_full_runs':   float,
        'away_bp_fip':      float,   # Rest-adjusted bullpen FIP
        'home_bp_fip':      float,
        'full_under_7_5_prob':  float,
        'full_under_8_5_prob':  float,
        'full_under_9_5_prob':  float,
        'full_over_7_5_prob':   float,
        'full_over_8_5_prob':   float,
        'full_over_9_5_prob':   float,
        # Plus all original F5 keys from run_monte_carlo_f5()
    }
"""

import numpy as np
import statsapi

from monte_carlo_f5 import (
    run_monte_carlo_f5,
    generate_generic_lineup,
    adjust_batter_rates,
    apply_environmental_physics,
    create_cdf_array,
    simulate_half_inning_vectorized,
    HOME_ADVANTAGE_FACTOR,
    _build_bullpen_lineup_states,
)
from fetch_lineups import get_batter_pa_rates, get_pitcher_hand
from bullpen_rest import get_adjusted_bullpen_fip
from umpire_engine import apply_umpire_sabermetric_layer

# Keys that receive the home field advantage multiplier
_HFA_KEYS = ('single', 'double', 'triple', 'hr', 'bb')

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# League-average starting pitcher is removed by inning 6 in most games.
# SP projected IP drives this — but we default to 6 IP (through inning 6).
DEFAULT_SP_IP = 6.0

# ---------------------------------------------------------------------------
# Late Inning Simulation Engine
# ---------------------------------------------------------------------------


def _simulate_late_innings(
    away_raw_lineup: list,
    home_raw_lineup: list,
    away_bp_fip: float,
    home_bp_fip: float,
    park_factor: float = 1.0,
    weather_context: dict = None,
    umpire_profile: dict = None,
    iterations: int = 10000,
    sp_exit_inning: int = 6,
    away_batter_start_idx: np.ndarray = None,
    home_batter_start_idx: np.ndarray = None,
) -> dict:
    """
    Simulates innings (sp_exit_inning) through 9 for both teams using
    their rest-adjusted bullpen FIP converted to PA rates.

    Parameters
    ----------
    away_raw_lineup / home_raw_lineup : list of batter dicts
    away_bp_fip / home_bp_fip         : rest-adjusted bullpen FIPs
    sp_exit_inning                     : first inning handled by bullpen (default 6)
    away_batter_start_idx              : array of batter positions carried over from F5
    home_batter_start_idx              : same for home team

    Returns
    -------
    dict with keys: away_late_runs, home_late_runs, late_total
    """
    n_late_innings = 9 - sp_exit_inning + 1   # e.g., 4 innings (6,7,8,9)

    # Build CDF lineup states for each team batting against opponent bullpen
    away_lineup_states = _build_bullpen_lineup_states(
        away_raw_lineup, home_bp_fip, park_factor, weather_context, umpire_profile,
        is_home=False
    )
    home_lineup_states = _build_bullpen_lineup_states(
        home_raw_lineup, away_bp_fip, park_factor, weather_context, umpire_profile,
        is_home=True
    )

    away_speed_tiers = np.array([b.get('speed_tier', 1) for b in away_raw_lineup])
    home_speed_tiers = np.array([b.get('speed_tier', 1) for b in home_raw_lineup])

    # Start batter index from where the F5 simulation left off
    if away_batter_start_idx is None:
        away_idx = np.zeros(iterations, dtype=np.int32)
    else:
        away_idx = away_batter_start_idx.copy()

    if home_batter_start_idx is None:
        home_idx = np.zeros(iterations, dtype=np.int32)
    else:
        home_idx = home_batter_start_idx.copy()

    away_late_runs = np.zeros(iterations, dtype=np.int32)
    home_late_runs = np.zeros(iterations, dtype=np.int32)

    # Bullpen TTO is always 0 (relievers pitch at most 1 inning each)
    away_tto = np.zeros(iterations, dtype=np.int32)
    home_tto = np.zeros(iterations, dtype=np.int32)

    outs   = np.zeros(iterations, dtype=np.int32)
    base1  = np.full(iterations, -1, dtype=np.int32)
    base2  = np.full(iterations, -1, dtype=np.int32)
    base3  = np.full(iterations, -1, dtype=np.int32)
    active = np.ones(iterations, dtype=bool)

    for _ in range(n_late_innings):
        # Top of inning (Away bats against home bullpen)
        outs.fill(0); base1.fill(-1); base2.fill(-1); base3.fill(-1); active.fill(True)
        simulate_half_inning_vectorized(
            active, away_lineup_states, away_idx, outs, away_late_runs,
            base1, base2, base3, away_speed_tiers, home_tto
        )

        # Bottom of inning (Home bats against away bullpen)
        outs.fill(0); base1.fill(-1); base2.fill(-1); base3.fill(-1); active.fill(True)
        simulate_half_inning_vectorized(
            active, home_lineup_states, home_idx, outs, home_late_runs,
            base1, base2, base3, home_speed_tiers, away_tto
        )

    return {
        'away_late_runs': float(np.mean(away_late_runs)),
        'home_late_runs': float(np.mean(home_late_runs)),
        'late_total':     float(np.mean(away_late_runs + home_late_runs)),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_full_game_mc(
    away_lineup_ids: list,
    home_lineup_ids: list,
    away_pitcher_name: str,
    home_pitcher_name: str,
    away_pitcher_fip: float,
    home_pitcher_fip: float,
    away_team_name: str,
    home_team_name: str,
    away_projected_ip: float = DEFAULT_SP_IP,
    home_projected_ip: float = DEFAULT_SP_IP,
    iterations: int = 10000,
    park_factor: float = 1.0,
    weather_context: dict = None,
    sport_id: int = 1,
    away_pitcher_hand: str = None,
    home_pitcher_hand: str = None,
    umpire_profile: dict = None,
    away_wrc: float = 100.0,
    home_wrc: float = 100.0,
    venue_name: str = None,
) -> dict:
    """
    Runs a full 9-inning Monte Carlo simulation combining:
      1. F5 MC simulation (innings 1-5) via run_monte_carlo_f5()
      2. Late innings (6-9) via _simulate_late_innings() using rest-adjusted bullpen FIPs

    Parameters
    ----------
    away_team_name / home_team_name : str
        Team names for bullpen FIP lookup (e.g. 'New York Mets', 'Cincinnati Reds').
    away_projected_ip / home_projected_ip : float
        Expected SP innings pitched. Determines when the bullpen takes over.
        Default 6.0 → bullpen enters inning 6.

    Returns
    -------
    dict with all F5 MC keys plus full game keys (see module docstring).
    """
    # Step 1: Fetch rest-adjusted bullpen FIPs so we can pass them to the F5 engine
    try:
        away_bp_fip = get_adjusted_bullpen_fip(away_team_name)
    except Exception:
        from run_daily_f5 import get_team_bullpen_fip
        away_bp_fip = get_team_bullpen_fip(away_team_name)

    try:
        home_bp_fip = get_adjusted_bullpen_fip(home_team_name)
    except Exception:
        from run_daily_f5 import get_team_bullpen_fip
        home_bp_fip = get_team_bullpen_fip(home_team_name)

    # Step 2: Run the F5 simulation (innings 1-5)
    f5_result = run_monte_carlo_f5(
        away_lineup_ids, home_lineup_ids,
        away_pitcher_name, home_pitcher_name,
        away_pitcher_fip, home_pitcher_fip,
        iterations=iterations,
        park_factor=park_factor,
        weather_context=weather_context,
        sport_id=sport_id,
        away_pitcher_hand=away_pitcher_hand,
        home_pitcher_hand=home_pitcher_hand,
        umpire_profile=umpire_profile,
        away_wrc=away_wrc,
        home_wrc=home_wrc,
        away_bp_fip=away_bp_fip,
        home_bp_fip=home_bp_fip,
        away_projected_ip=away_projected_ip,
        home_projected_ip=home_projected_ip,
        away_team_name=away_team_name,
        home_team_name=home_team_name,
        venue_name=venue_name,
    )



    # Step 3: Build confirmed lineups for late innings
    # (same lineup IDs as F5, but now hitting against bullpens)
    from fetch_lineups import get_batter_pa_rates
    from umpire_engine import apply_umpire_sabermetric_layer

    def _build_raw_lineup(lineup_ids, pitcher_hand, is_generic=False, wrc=100.0):
        if is_generic or not lineup_ids:
            generic_raw = generate_generic_lineup(pitcher_hand=pitcher_hand)
            if wrc and wrc != 100.0:
                wrc_scale = (wrc / 100.0) ** 0.5
                for b in generic_raw:
                    for k in ('bb', 'hr', 'single', 'double', 'triple'):
                        b[k] *= wrc_scale
                    b['out_rate'] = max(0.0001, 1.0 - sum(
                        v for key, v in b.items() if key not in ('out_rate', 'hand', 'speed_tier')))
            return generic_raw
        raw = []
        for pid in lineup_ids:
            rates = get_batter_pa_rates(pid, pitcher_hand=pitcher_hand)
            rates['hand'] = 'L'   # default; platoon is embedded in the per-PA rates
            rates['speed_tier'] = 1
            raw.append(rates)
        return raw

    away_is_generic = not bool(away_lineup_ids)
    home_is_generic = not bool(home_lineup_ids)

    away_raw = _build_raw_lineup(away_lineup_ids, home_pitcher_hand or 'R',
                                  away_is_generic, away_wrc)
    home_raw = _build_raw_lineup(home_lineup_ids, away_pitcher_hand or 'R',
                                  home_is_generic, home_wrc)

    # Step 4: Determine SP exit inning
    # If projected IP = 6.0, bullpen enters inning 6 (full late block = innings 6-9)
    # If projected IP = 5.0, bullpen enters inning 6 but SP only went 5 (still 4 late innings)
    # Conservative: always use 4 late innings (6-9) regardless of SP IP.
    # Future enhancement: use actual SP IP exit distribution.
    sp_exit_inning = max(6, min(8, round(away_projected_ip) + 1))
    # Use away SP exit as reference (we could model each side separately in future)

    # Step 5: Simulate innings 6-9
    late_result = _simulate_late_innings(
        away_raw, home_raw,
        away_bp_fip, home_bp_fip,
        park_factor=park_factor,
        weather_context=weather_context,
        umpire_profile=umpire_profile,
        iterations=iterations,
        sp_exit_inning=sp_exit_inning,
    )

    # Step 6: Combine F5 + Late
    away_full = f5_result['away_mc_runs'] + late_result['away_late_runs']
    home_full = f5_result['home_mc_runs'] + late_result['home_late_runs']
    full_total = away_full + home_full

    # Full game probability distributions (common lines: 7.5, 8.5, 9.5)
    # Approximate using a Poisson distribution centered on full_total
    import math

    def _poisson_over_prob(mean, line):
        """P(X > line) for Poisson distribution."""
        k = int(math.floor(line))
        prob_under_or_equal = sum(
            (math.exp(-mean) * (mean ** i)) / math.factorial(i)
            for i in range(k + 1)
        )
        return max(0.0, min(1.0, 1.0 - prob_under_or_equal))

    result = {
        # Full game totals
        'full_game_total':      round(full_total, 2),
        'away_full_runs':       round(away_full, 2),
        'home_full_runs':       round(home_full, 2),

        # Component breakdown
        'f5_total':             f5_result['mc_total_runs'],
        'late_total':           round(late_result['late_total'], 2),
        'away_late_runs':       round(late_result['away_late_runs'], 2),
        'home_late_runs':       round(late_result['home_late_runs'], 2),

        # Bullpen context
        'away_bp_fip':          round(away_bp_fip, 2),
        'home_bp_fip':          round(home_bp_fip, 2),
        'away_sp_exit_inning':  sp_exit_inning,

        # Full game over/under probabilities
        'full_over_7_5_prob':   round(_poisson_over_prob(full_total, 7.5), 3),
        'full_over_8_5_prob':   round(_poisson_over_prob(full_total, 8.5), 3),
        'full_over_9_5_prob':   round(_poisson_over_prob(full_total, 9.5), 3),
        'full_under_7_5_prob':  round(1.0 - _poisson_over_prob(full_total, 7.5), 3),
        'full_under_8_5_prob':  round(1.0 - _poisson_over_prob(full_total, 8.5), 3),
        'full_under_9_5_prob':  round(1.0 - _poisson_over_prob(full_total, 9.5), 3),
    }

    # Merge F5 results
    result.update(f5_result)
    return result


# ---------------------------------------------------------------------------
# CLI: quick test for a single game
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import statsapi
    from fetch_lineups import get_lineup_for_game
    from run_daily_f5 import get_pitcher_projected_ip

    from mlb_time import get_mlb_now
    today = get_mlb_now().strftime('%m/%d/%Y')
    games = statsapi.schedule(sportId=1, date=today)

    if not games:
        print("No games today.")
    else:
        game = games[0]
        gid  = game['game_id']
        away = game['away_name']
        home = game['home_name']
        ap   = game.get('away_probable_pitcher', 'TBD')
        hp   = game.get('home_probable_pitcher', 'TBD')

        print(f"Testing Full Game MC: {away} @ {home}")
        print(f"Pitchers: {ap} vs {hp}")

        lineups = get_lineup_for_game(gid)

        result = run_full_game_mc(
            lineups['away'], lineups['home'],
            ap, hp, 4.20, 4.20,
            away_team_name=away,
            home_team_name=home,
            iterations=10000,
        )

        print(f"\n--- Results ---")
        print(f"F5 Total:         {result['f5_total']} runs")
        print(f"Late Total (6-9): {result['late_total']} runs")
        print(f"Full Game Total:  {result['full_game_total']} runs")
        print(f"Away BP FIP:      {result['away_bp_fip']}  |  Home BP FIP: {result['home_bp_fip']}")
        print(f"Over 7.5:  {result['full_over_7_5_prob']:.1%}")
        print(f"Over 8.5:  {result['full_over_8_5_prob']:.1%}")
        print(f"Over 9.5:  {result['full_over_9_5_prob']:.1%}")
