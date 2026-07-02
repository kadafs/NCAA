"""
monte_carlo_t20.py
==================
Vectorized T20 cricket innings simulator.

Key structural patches vs standard MC engine:
  1. Striker rotation: odd runs + mandatory over-end swap
  2. Wide/No-ball guard: extras don't count toward over_balls counter
  3. Batter settled-in boost: inverse TTTO (boundary rate climbs, dot rate drops)
  4. Powerplay extraction: overs 1-6 tracked separately for primary market
"""

import numpy as np
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ground_factors import get_ground_factor, get_powerplay_factor, DEW_FACTOR_MODIFIER

# ---------------------------------------------------------------------------
# T20 League Baselines
# ---------------------------------------------------------------------------
LEAGUE_DOT_RATE      = 0.380
LEAGUE_SINGLE_RATE   = 0.360   # 1s and 2s combined
LEAGUE_BOUNDARY_RATE = 0.155   # 4s and 6s combined
LEAGUE_WICKET_RATE   = 0.048
LEAGUE_WIDE_RATE     = 0.040


def log_odds_blend(bowler_rate: float, batter_rate: float, league_rate: float) -> float:
    """Combines bowler and batter rates against league baseline using Log-Odds."""
    bowler_rate = max(0.001, min(0.999, bowler_rate))
    batter_rate = max(0.001, min(0.999, batter_rate))
    league_rate = max(0.001, min(0.999, league_rate))

    p_odds = bowler_rate / (1.0 - bowler_rate)
    b_odds = batter_rate / (1.0 - batter_rate)
    l_odds = league_rate / (1.0 - league_rate)

    combined_odds = (p_odds * b_odds) / l_odds
    return combined_odds / (1.0 + combined_odds)


def _apply_settled_boost(boundary_pct: np.ndarray, dot_pct: np.ndarray,
                          balls_faced: np.ndarray) -> tuple:
    """
    Vectorized batter settled-in boost.
    Batters who have faced 10+ balls get progressively more aggressive:
      boundary_pct climbs, dot_pct falls (inverse TTTO).
    Capped at 35% uplift after ~33 balls faced.
    """
    boost = np.ones(len(balls_faced))
    mask = balls_faced >= 10
    boost[mask] = np.minimum(1.35, 1.0 + (balls_faced[mask] - 10) * 0.015)

    adjusted_boundary = boundary_pct * boost
    adjusted_dot      = dot_pct * (2.0 - boost)  # linear drop
    return adjusted_boundary, adjusted_dot


def simulate_innings_vectorized(
    iterations: int,
    batting_lineup: list,
    bowling_rotation: list,
    ground_factor: float = 1.00,
    is_chasing: bool = False,
    dew_present: bool = False,
) -> dict:
    """
    Execute a high-performance, 20-over vectorized T20 innings simulation.

    Parameters
    ----------
    iterations      : number of parallel game simulations
    batting_lineup  : list of 11 batter profile dicts (index 0 = opener)
    bowling_rotation: list of bowler profile dicts (up to 5 bowlers, each bowls 4 overs max)
    ground_factor   : run scaling multiplier from ground_factors.py
    is_chasing      : True if batting second (dew factor applied if dew_present)
    dew_present     : True for evening matches in subcontinent/Asia

    Returns
    -------
    dict with: expected_total_runs, expected_powerplay_runs, expected_wickets,
               distribution arrays for O/U line analysis
    """
    # Dew modifier for chasing team
    dew_mod = DEW_FACTOR_MODIFIER if (is_chasing and dew_present) else 1.00

    # -----------------------------------------------------------------------
    # 1. Initialize State Vectors (shape: iterations)
    # -----------------------------------------------------------------------
    runs              = np.zeros(iterations, dtype=np.int32)
    powerplay_runs    = np.zeros(iterations, dtype=np.int32)
    wickets           = np.zeros(iterations, dtype=np.int32)
    over_balls        = np.zeros(iterations, dtype=np.int32)   # 0-5 within current over
    overs_completed   = np.zeros(iterations, dtype=np.int32)   # 0-19

    # Batting pointer arrays
    striker_idx       = np.zeros(iterations, dtype=np.int32)   # index into batting_lineup
    non_striker_idx   = np.ones(iterations,  dtype=np.int32)
    next_batter_idx   = np.full(iterations, 2, dtype=np.int32) # next man in at #3

    # Balls faced matrix: shape (iterations, 11) — tracks each batter's exposure
    balls_faced_matrix = np.zeros((iterations, 11), dtype=np.int32)

    # Execution mask
    active = np.ones(iterations, dtype=bool)

    # Bowling quota tracker: each bowler limited to 4 overs (24 balls)
    # Map over number → bowler index using round-robin respecting quotas
    num_bowlers = len(bowling_rotation)
    bowler_quota = np.zeros(num_bowlers, dtype=np.int32)  # overs bowled per bowler

    def _assign_bowler(current_over: int) -> int:
        """Select bowler for current over — simple quota-respecting rotation."""
        for attempt in range(num_bowlers):
            idx = (current_over + attempt) % num_bowlers
            if bowler_quota[idx] < 4:
                return idx
        return current_over % num_bowlers  # fallback

    # -----------------------------------------------------------------------
    # 2. Delivery Event Loop
    # -----------------------------------------------------------------------
    while np.any(active):
        idx = np.where(active)[0]
        num_active = len(idx)

        curr_strikers    = striker_idx[idx]
        curr_overs_arr   = overs_completed[idx]

        # --- Build delivery probability arrays ---
        prob_wicket   = np.zeros(num_active)
        prob_extra    = np.zeros(num_active)
        prob_dot      = np.zeros(num_active)
        prob_boundary = np.zeros(num_active)

        # Get current balls faced for each active striker
        active_balls_faced = balls_faced_matrix[idx, curr_strikers]

        # Build batter and bowler base rates for each game
        # (vectorized by batching per batter/bowler combination)
        batter_boundary = np.array([batting_lineup[s].get('boundary_pct', 0.15) for s in curr_strikers])
        batter_dot      = np.array([batting_lineup[s].get('dot_pct', 0.38) for s in curr_strikers])
        batter_dismiss  = np.array([batting_lineup[s].get('dismissal_rate', 0.048) for s in curr_strikers])

        # Apply settled-in boost
        batter_boundary, batter_dot = _apply_settled_boost(batter_boundary, batter_dot, active_balls_faced)

        # Apply ground/dew scaling to batting rates
        batter_boundary = batter_boundary * ground_factor * dew_mod

        # Bowler selection per over
        curr_bowler_idx = np.array([_assign_bowler(int(o)) for o in curr_overs_arr])
        bowler_wicket   = np.array([bowling_rotation[b].get('wicket_rate', 0.048) for b in curr_bowler_idx])
        bowler_dot      = np.array([bowling_rotation[b].get('dot_rate', 0.38) for b in curr_bowler_idx])
        bowler_boundary = np.array([bowling_rotation[b].get('boundary_rate', 0.12) for b in curr_bowler_idx])
        bowler_wide     = np.array([bowling_rotation[b].get('wide_rate', 0.04) for b in curr_bowler_idx])

        # Log-odds blends for each event
        for k in range(num_active):
            prob_wicket[k]   = log_odds_blend(bowler_wicket[k],   batter_dismiss[k],  LEAGUE_WICKET_RATE)
            prob_dot[k]      = log_odds_blend(bowler_dot[k],      batter_dot[k],      LEAGUE_DOT_RATE)
            prob_boundary[k] = log_odds_blend(bowler_boundary[k], batter_boundary[k], LEAGUE_BOUNDARY_RATE)
            prob_extra[k]    = bowler_wide[k]  # wides/no-balls: bowler accuracy only

        # Normalize to 1.0
        total_p = prob_wicket + prob_extra + prob_dot + prob_boundary
        # single/2 fills remaining probability
        prob_single = np.maximum(0.0, 1.0 - total_p)
        total_p_adj = prob_wicket + prob_extra + prob_dot + prob_boundary + prob_single

        prob_wicket   /= total_p_adj
        prob_extra    /= total_p_adj
        prob_dot      /= total_p_adj
        prob_boundary /= total_p_adj
        # prob_single = remaining

        # --- Roll random variables ---
        r = np.random.rand(num_active)

        cum = prob_wicket
        ev_wicket   = r < cum
        cum_e = cum + prob_extra
        ev_extra    = (~ev_wicket) & (r < cum_e)
        cum_d = cum_e + prob_dot
        ev_dot      = (~ev_wicket) & (~ev_extra) & (r < cum_d)
        cum_b = cum_d + prob_boundary
        ev_boundary = (~ev_wicket) & (~ev_extra) & (~ev_dot) & (r < cum_b)
        ev_single   = (~ev_wicket) & (~ev_extra) & (~ev_dot) & (~ev_boundary)

        in_powerplay = curr_overs_arr < 6

        # -----------------------------------------------------------------------
        # STRUCTURAL TRAP 2: Extra allocations — wides/no-balls
        # Extras give 1 run but do NOT increment over_balls
        # -----------------------------------------------------------------------
        extra_global = idx[ev_extra]
        runs[extra_global] += 1
        powerplay_runs[extra_global[in_powerplay[ev_extra]]] += 1
        # over_balls NOT incremented for extras

        # -----------------------------------------------------------------------
        # Legal delivery processing
        # -----------------------------------------------------------------------
        legal_mask = ~ev_extra
        legal_idx  = idx[legal_mask]

        if len(legal_idx) > 0:
            legal_strikers   = striker_idx[legal_idx]
            legal_over       = overs_completed[legal_idx]
            in_pp_legal      = legal_over < 6

            # Increment ball counters for legal deliveries
            over_balls[legal_idx]  += 1
            balls_faced_matrix[legal_idx, legal_strikers] += 1

            # -- Wickets --
            w_sub = ev_wicket[legal_mask]
            if np.any(w_sub):
                w_idx = legal_idx[w_sub]
                wickets[w_idx] += 1
                avail = next_batter_idx[w_idx]
                valid = avail < 11
                striker_idx[w_idx[valid]] = avail[valid]
                next_batter_idx[w_idx] += 1

            # -- Boundaries (4s and 6s) --
            b_sub = ev_boundary[legal_mask]
            if np.any(b_sub):
                b_idx = legal_idx[b_sub]
                b_strikers = striker_idx[b_idx]
                # High-ISO batters hit more 6s
                six_prob = np.array([min(0.45, batting_lineup[s].get('boundary_pct', 0.15) * 2.0) for s in b_strikers])
                is_six = np.random.rand(len(b_idx)) < six_prob
                boundary_runs = np.where(is_six, 6, 4)
                runs[b_idx] += boundary_runs
                powerplay_runs[b_idx[in_pp_legal[b_sub]]] += boundary_runs[in_pp_legal[b_sub]]

                # Even runs — striker stays (no rotation needed for boundaries)

            # -- Singles/Twos --
            s_sub = ev_single[legal_mask]
            if np.any(s_sub):
                s_idx = legal_idx[s_sub]
                # 80% singles (1 run), 20% twos (2 runs)
                run_vals = np.where(np.random.rand(len(s_idx)) < 0.80, 1, 2)
                runs[s_idx] += run_vals
                powerplay_runs[s_idx[in_pp_legal[s_sub]]] += run_vals[in_pp_legal[s_sub]]

                # -----------------------------------------------------------------------
                # STRUCTURAL TRAP 1: Striker rotation — odd runs swap striker/non-striker
                # -----------------------------------------------------------------------
                odd_run_mask = (run_vals % 2 == 1)
                if np.any(odd_run_mask):
                    rot = s_idx[odd_run_mask]
                    striker_idx[rot], non_striker_idx[rot] = (
                        non_striker_idx[rot].copy(),
                        striker_idx[rot].copy(),
                    )

            # -----------------------------------------------------------------------
            # STRUCTURAL TRAP 1: Over-end mandatory rotation
            # Every 6 legal deliveries, non-striker becomes striker
            # -----------------------------------------------------------------------
            over_complete = over_balls[legal_idx] == 6
            if np.any(over_complete):
                oc_idx = legal_idx[over_complete]
                overs_completed[oc_idx] += 1
                over_balls[oc_idx] = 0

                # Mandatory striker swap at end of over
                striker_idx[oc_idx], non_striker_idx[oc_idx] = (
                    non_striker_idx[oc_idx].copy(),
                    striker_idx[oc_idx].copy(),
                )
                # Update bowler quota for the over that just ended
                for ov_val in curr_overs_arr[legal_mask][over_complete]:
                    bowler_idx_used = _assign_bowler(int(ov_val))
                    bowler_quota[bowler_idx_used] = min(4, bowler_quota[bowler_idx_used] + 1)

        # -----------------------------------------------------------------------
        # Innings termination: 10 wickets OR 20 overs completed
        # -----------------------------------------------------------------------
        active = (overs_completed < 20) & (wickets < 10)

    # -----------------------------------------------------------------------
    # 3. Results
    # -----------------------------------------------------------------------
    return {
        'expected_total_runs':      round(float(np.mean(runs)), 1),
        'expected_powerplay_runs':  round(float(np.mean(powerplay_runs)), 1),
        'expected_wickets':         round(float(np.mean(wickets)), 1),

        # O/U line probabilities for powerplay
        'pp_over_40_prob':  round(float(np.mean(powerplay_runs > 40)),  3),
        'pp_over_45_prob':  round(float(np.mean(powerplay_runs > 45)),  3),
        'pp_over_50_prob':  round(float(np.mean(powerplay_runs > 50)),  3),
        'pp_over_55_prob':  round(float(np.mean(powerplay_runs > 55)),  3),
        'pp_under_40_prob': round(float(np.mean(powerplay_runs < 40)),  3),
        'pp_under_45_prob': round(float(np.mean(powerplay_runs < 45)),  3),
        'pp_under_50_prob': round(float(np.mean(powerplay_runs < 50)),  3),

        # Full innings O/U
        'over_155_prob':    round(float(np.mean(runs > 155)), 3),
        'over_165_prob':    round(float(np.mean(runs > 165)), 3),
        'over_175_prob':    round(float(np.mean(runs > 175)), 3),
        'over_185_prob':    round(float(np.mean(runs > 185)), 3),

        # Raw arrays for custom line analysis
        'raw_runs':           runs.tolist(),
        'raw_powerplay_runs': powerplay_runs.tolist(),
    }


def run_t20_match_mc(
    team1_batting: list,
    team2_batting: list,
    team1_bowling: list,
    team2_bowling: list,
    venue_name: str = 'Unknown',
    iterations: int = 10000,
) -> dict:
    """
    Run both innings and combine into full match projection.

    Parameters
    ----------
    team1_batting / team2_batting : list of 11 batter profile dicts
    team1_bowling / team2_bowling : list of bowler profile dicts
    venue_name                    : ground name for factor lookup

    Returns
    -------
    dict with both innings projections + combined match total
    """
    gf_data = get_ground_factor(venue_name)
    gf = gf_data['factor']
    dew = gf_data['dew']
    pp_factor = get_powerplay_factor(venue_name)

    # Team 1 bats first (no dew)
    t1 = simulate_innings_vectorized(
        iterations, team1_batting, team2_bowling,
        ground_factor=gf, is_chasing=False, dew_present=dew,
    )

    # Team 2 bats second (may benefit from dew)
    t2 = simulate_innings_vectorized(
        iterations, team2_batting, team1_bowling,
        ground_factor=gf, is_chasing=True, dew_present=dew,
    )

    combined_runs = np.array(t1['raw_runs']) + np.array(t2['raw_runs'])
    pp_combined   = np.array(t1['raw_powerplay_runs']) + np.array(t2['raw_powerplay_runs'])

    return {
        'team1_innings': t1,
        'team2_innings': t2,

        'expected_match_total':     round(float(np.mean(combined_runs)), 1),
        'expected_pp_combined':     round(float(np.mean(pp_combined)), 1),

        # Combined PP O/U
        'pp_combined_over_85_prob':  round(float(np.mean(pp_combined > 85)),  3),
        'pp_combined_over_90_prob':  round(float(np.mean(pp_combined > 90)),  3),
        'pp_combined_over_95_prob':  round(float(np.mean(pp_combined > 95)),  3),
        'pp_combined_over_100_prob': round(float(np.mean(pp_combined > 100)), 3),
        'pp_combined_under_85_prob': round(float(np.mean(pp_combined < 85)),  3),
        'pp_combined_under_90_prob': round(float(np.mean(pp_combined < 90)),  3),

        # Team 1 win probability (scored more)
        'team1_win_prob': round(float(np.mean(np.array(t1['raw_runs']) > np.array(t2['raw_runs']))), 3),
        'team2_win_prob': round(float(np.mean(np.array(t2['raw_runs']) > np.array(t1['raw_runs']))), 3),

        'venue': venue_name,
        'ground_factor': gf,
        'dew_present': dew,
    }


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Test with generic profiles
    generic_batter = {
        'boundary_pct': 0.15, 'dot_pct': 0.38,
        'dismissal_rate': 0.048, 'strike_rate': 135.0,
    }
    elite_batter = {
        'boundary_pct': 0.22, 'dot_pct': 0.30,
        'dismissal_rate': 0.040, 'strike_rate': 155.0,
    }
    generic_bowler = {
        'wicket_rate': 0.048, 'dot_rate': 0.38,
        'boundary_rate': 0.12, 'wide_rate': 0.04,
    }
    elite_bowler = {
        'wicket_rate': 0.070, 'dot_rate': 0.45,
        'boundary_rate': 0.08, 'wide_rate': 0.025,
    }

    batting_side = [elite_batter, elite_batter] + [generic_batter] * 9
    bowling_side = [elite_bowler] * 2 + [generic_bowler] * 3

    print("=== T20 Innings Simulation Test ===")
    result = simulate_innings_vectorized(
        10000, batting_side, bowling_side,
        ground_factor=1.05, is_chasing=False, dew_present=True
    )
    print(f"Expected total runs:     {result['expected_total_runs']}")
    print(f"Expected powerplay runs: {result['expected_powerplay_runs']}")
    print(f"Expected wickets:        {result['expected_wickets']}")
    print(f"PP Over 50 prob:         {result['pp_over_50_prob']:.1%}")
    print(f"PP Under 50 prob:        {result['pp_under_50_prob']:.1%}")
