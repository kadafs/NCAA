"""
tennis_markov.py
================
Analytical Markov chain + Monte Carlo set/match simulation engine.

Architecture:
  Point level  -> Analytical formula (instant, no MC loop)
  Game level   -> p_server_wins_game(p) analytical solution
  Set level    -> Monte Carlo (handles tiebreaks, alternating serve)
  Match level  -> Monte Carlo (best-of-3 or best-of-5)

Returns total game distributions for O/U line comparison,
first set winner probabilities, and match winner probabilities.
"""

import numpy as np


# ---------------------------------------------------------------------------
# Core Analytical Functions
# ---------------------------------------------------------------------------

def log_odds_blend(rate_a: float, rate_b: float, league_rate: float) -> float:
    """Combines two rates against league baseline using Log-Odds formulation."""
    rate_a = max(0.001, min(0.999, rate_a))
    rate_b = max(0.001, min(0.999, rate_b))
    league_rate = max(0.001, min(0.999, league_rate))

    a_odds = rate_a / (1.0 - rate_a)
    b_odds = rate_b / (1.0 - rate_b)
    l_odds = league_rate / (1.0 - league_rate)

    combined_odds = (a_odds * b_odds) / l_odds
    return combined_odds / (1.0 + combined_odds)


def p_server_wins_game(p: float) -> float:
    """
    Analytical probability that server wins a game given p = P(server wins point).

    Formula breakdown:
      p^4            -> win to love (40-0)
      4p^4(1-p)      -> win to 15  (40-15)
      10p^4(1-p)^2   -> win to 30  (40-30)
      deuce_term     -> P(reach deuce) x P(win from deuce)
                      = 20p^3(1-p)^3 x [p^2 / (1 - 2p(1-p))]
    """
    p = max(0.01, min(0.99, p))
    q = 1.0 - p
    p_deuce = 20.0 * (p ** 3) * (q ** 3)
    p_win_from_deuce = (p ** 2) / (1.0 - 2.0 * p * q)

    return (p ** 4) + 4.0 * (p ** 4) * q + 10.0 * (p ** 4) * (q ** 2) + p_deuce * p_win_from_deuce


# ---------------------------------------------------------------------------
# Surface and league constants imported from surface_engine (single source of
# truth). Do NOT redefine SURFACE_POINT_ADJUSTMENTS here -- that pattern was
# the additive double-correction bug identified in the audit.
# ---------------------------------------------------------------------------
from surface_engine import get_surface_modifier, get_league_hold



def blended_serve_win_prob(
    server_fsw: float,
    server_ssw: float,
    server_fsp: float,
    returner_rpw: float,
    surface: str,
    tour: str,
) -> float:
    """
    Derives blended point-level probability that server wins a point on serve.

    Pipeline (audit-corrected, Finding 1):
      1. Compute raw serve rate from player's FSP/FSW/SSW.
      2. Apply SURFACE_MODIFIERS multiplicatively (not additive shift).
         Multiplicative scaling in log-odds space preserves S-curve boundary
         behavior at the talent extremes (weak qualifiers are not over-penalized).
      3. Apply 0.55 power transform to all three inputs before log-odds blend
         to ensure consistent scale across the game-level hold space.
      4. log_odds_blend uses game-level league hold rate as the anchor.

    Parameters
    ----------
    server_fsw   : First serve win % (e.g. 0.74)
    server_ssw   : Second serve win % (e.g. 0.52)
    server_fsp   : First serve in % (e.g. 0.61)
    returner_rpw : Returner's return points won % (e.g. 0.38)
    surface      : 'Hard', 'Clay', or 'Grass'
    tour         : 'ATP' or 'WTA'

    Returns
    -------
    float : P(server wins this point on serve)
    """
    # 1. Server's raw combined serve rate
    raw_serve = server_fsp * server_fsw + (1.0 - server_fsp) * server_ssw

    # 2. Apply surface multiplier to server only (serve dominance is asymmetric)
    surface_mod = get_surface_modifier(tour, surface)
    server_adj  = max(0.01, min(0.99, raw_serve * surface_mod))

    # 3. Returner's implied point-win rate from SERVER perspective
    returner_adj = max(0.01, min(0.99, 1.0 - returner_rpw))

    # 4. League game-level hold rate as log-odds anchor
    league_hold = get_league_hold(tour)

    # 5. Power compress all three into a consistent scale, then log-odds blend.
    #    The 0.55 exponent is a shrinkage factor that maps the [0,1] interval
    #    symmetrically — boundary-preserving and non-linear in the center.
    s_point = server_adj  ** 0.55
    r_point = returner_adj ** 0.55
    l_point = league_hold  ** 0.55

    return max(0.01, min(0.99, log_odds_blend(s_point, r_point, l_point)))


# ---------------------------------------------------------------------------
# Tiebreak Simulation
# ---------------------------------------------------------------------------

def simulate_tiebreak_vectorized(
    p_p1_serve: float,
    p_p2_serve: float,
    num_active: int,
    p1_serves_first_in_tb: np.ndarray,
) -> np.ndarray:
    """
    Simulates a standard 7-point tennis tiebreak for a vector of active games.

    Serving sequence in a tiebreak:
      P1 serves point 1, P2 serves 2-3, P1 serves 4-5, P2 serves 6-7, ...
      At deuce (6-6) the pair pattern continues (not single-point alternation).

    Parameters
    ----------
    p_p1_serve         : P(P1 wins point when serving)
    p_p2_serve         : P(P2 wins point when serving)
    num_active         : number of active tiebreaks to simulate
    p1_serves_first_in_tb : bool array (length=num_active); True where P1
                            serves the first tiebreak point.  This is
                            determined by the set's initial server and the
                            game count at 6-6, NOT assumed to always be P1.

    Returns
    -------
    np.ndarray[bool] : True where Player 1 won the tiebreak
    """
    p1_pts   = np.zeros(num_active, dtype=np.int32)
    p2_pts   = np.zeros(num_active, dtype=np.int32)
    total_pts = np.zeros(num_active, dtype=np.int32)
    tb_active = np.ones(num_active, dtype=bool)

    # P2-serves-first anchor (per simulation); fixed at tiebreak start.
    p2_serves_first = ~p1_serves_first_in_tb  # shape: (num_active,)

    while np.any(tb_active):
        idx = np.where(tb_active)[0]

        # Sequence index: 0 → first server's turn, 1 → second server's turn
        # Standard pattern: 1, 2, 2, 1, 1, 2, 2, 1, 1, ...
        seq = ((total_pts[idx] + 1) // 2) % 2   # 0 = first server, 1 = second server

        # is_p2_serving is True when it's the second server's turn AND P2 is the
        # second server (p1_serves_first), OR when it's the first server's turn
        # AND P2 is the first server (~p1_serves_first).
        #   seq==1 XOR p2_serves_first => handles both orientations cleanly.
        is_p2_serving = (seq == 1) ^ p2_serves_first[idx]

        p_win = np.where(is_p2_serving, 1.0 - p_p2_serve, p_p1_serve)

        r = np.random.rand(len(idx))
        p1_won = r < p_win

        p1_pts[idx[p1_won]]  += 1
        p2_pts[idx[~p1_won]] += 1
        total_pts[idx]        += 1

        # Must reach 7+ and lead by 2+ (standard tiebreak)
        p1_wins = (p1_pts[idx] >= 7) & ((p1_pts[idx] - p2_pts[idx]) >= 2)
        p2_wins = (p2_pts[idx] >= 7) & ((p2_pts[idx] - p1_pts[idx]) >= 2)
        tb_active[idx[p1_wins | p2_wins]] = False

    return p1_pts > p2_pts


# ---------------------------------------------------------------------------
# Full Match Monte Carlo Simulation
# ---------------------------------------------------------------------------

def simulate_match_monte_carlo(
    p1_stats: dict,
    p2_stats: dict,
    tour: str,
    surface: str,
    tournament_name: str,
    iterations: int = 10000,
) -> dict:
    """
    Full match simulation: analytical game probabilities + MC set/match.

    Parameters
    ----------
    p1_stats / p2_stats : dict with keys:
        first_serve_pct, first_serve_win_pct, second_serve_win_pct,
        return_points_won_pct
    tour              : 'ATP' or 'WTA'
    surface           : 'Hard', 'Clay', or 'Grass'
    tournament_name   : e.g. 'Wimbledon' (determines Best-of-3 vs Best-of-5)
    iterations        : number of match simulations (default 10,000)

    Returns
    -------
    dict with:
      p1_match_win_prob, p2_match_win_prob,
      p1_first_set_win_prob, expected_total_games,
      over/under probabilities for common lines,
      raw_game_distribution (list)
    """
    from surface_engine import sets_to_win as _sets_to_win

    sets_target = _sets_to_win(tour, tournament_name)

    # -- Derive Blended Point Probabilities --
    p1_p = blended_serve_win_prob(
        p1_stats['first_serve_win_pct'],
        p1_stats['second_serve_win_pct'],
        p1_stats['first_serve_pct'],
        p2_stats['return_points_won_pct'],
        surface=surface,
        tour=tour,
    )
    p2_p = blended_serve_win_prob(
        p2_stats['first_serve_win_pct'],
        p2_stats['second_serve_win_pct'],
        p2_stats['first_serve_pct'],
        p1_stats['return_points_won_pct'],
        surface=surface,
        tour=tour,
    )

    # -- Analytical Game Probabilities --
    p1_game_prob = p_server_wins_game(p1_p)
    p2_game_prob = p_server_wins_game(p2_p)

    # -- Initialize Match-Level Arrays --
    match_active = np.ones(iterations, dtype=bool)
    p1_sets = np.zeros(iterations, dtype=np.int32)
    p2_sets = np.zeros(iterations, dtype=np.int32)
    total_games = np.zeros(iterations, dtype=np.int32)
    first_set_winners = np.zeros(iterations, dtype=np.int32)

    # Track which player serves first each set (alternates after each set)
    p1_serves_first = np.ones(iterations, dtype=bool)

    current_set_num = 0

    while np.any(match_active):
        idx = np.where(match_active)[0]
        num_active = len(idx)

        p1_games = np.zeros(num_active, dtype=np.int32)
        p2_games = np.zeros(num_active, dtype=np.int32)
        game_num = np.zeros(num_active, dtype=np.int32)
        set_active = np.ones(num_active, dtype=bool)

        while np.any(set_active):
            s_idx = np.where(set_active)[0]

            # Determine who serves this game
            # p1_serves_first toggles per set; within a set, odd/even game_num alternates
            is_p1_serving_set = p1_serves_first[idx[s_idx]]
            is_p1_serving = (game_num[s_idx] % 2 == 0) == is_p1_serving_set

            # Game win probability from server's perspective
            p1_win_game_prob = np.where(
                is_p1_serving,
                p1_game_prob,              # P1 serving: P(P1 holds)
                1.0 - p2_game_prob,        # P2 serving: P(P1 breaks)
            )

            r_game = np.random.rand(len(s_idx))
            p1_won_game = r_game < p1_win_game_prob

            p1_games[s_idx[p1_won_game]] += 1
            p2_games[s_idx[~p1_won_game]] += 1
            game_num[s_idx] += 1
            total_games[idx[s_idx]] += 1

            # Standard set: must reach 6 games and lead by 2
            p1_wins_set = (p1_games[s_idx] >= 6) & ((p1_games[s_idx] - p2_games[s_idx]) >= 2)
            p2_wins_set = (p2_games[s_idx] >= 6) & ((p2_games[s_idx] - p1_games[s_idx]) >= 2)

            # Tiebreak at 6-6
            tiebreak_mask = (p1_games[s_idx] == 6) & (p2_games[s_idx] == 6)
            if np.any(tiebreak_mask):
                tb_sub = s_idx[tiebreak_mask]

                # Determine tiebreak opener: same player who serves game 13 in set.
                # At 6-6, game_num[tb_sub] == 12; the rule mirrors the set-level logic:
                #   P1 serves TB first iff P1 was the set's initial server
                #   (since game_num=12 is even, and even games go to the initial server).
                p1_serves_tb = p1_serves_first[idx[tb_sub]]

                p1_won_tb = simulate_tiebreak_vectorized(
                    p1_p, p2_p, len(tb_sub),
                    p1_serves_first_in_tb=p1_serves_tb,
                )

                p1_games[tb_sub[p1_won_tb]] += 1
                p2_games[tb_sub[~p1_won_tb]] += 1
                total_games[idx[tb_sub]] += 1  # tiebreak = 1 additional game

                # Re-check set completion after tiebreak
                p1_wins_set = (p1_games[s_idx] >= 7) | ((p1_games[s_idx] >= 6) & ((p1_games[s_idx] - p2_games[s_idx]) >= 2))
                p2_wins_set = (p2_games[s_idx] >= 7) | ((p2_games[s_idx] >= 6) & ((p2_games[s_idx] - p1_games[s_idx]) >= 2))

            set_complete = p1_wins_set | p2_wins_set
            set_active[s_idx[set_complete]] = False

        # Compile set results
        p1_won_set = p1_games > p2_games
        p1_sets[idx[p1_won_set]] += 1
        p2_sets[idx[~p1_won_set]] += 1

        # First set winner tracking (isolated from fatigue noise)
        if current_set_num == 0:
            first_set_winners[idx[p1_won_set]] = 1
            first_set_winners[idx[~p1_won_set]] = 2

        # Alternate server for next set
        p1_serves_first[idx] = ~p1_serves_first[idx]

        # Match completion check
        p1_wins_match = p1_sets[idx] >= sets_target
        p2_wins_match = p2_sets[idx] >= sets_target
        match_active[idx[p1_wins_match | p2_wins_match]] = False
        current_set_num += 1

    # -- Extract Distribution Statistics --
    p1_match_wins = np.sum(p1_sets >= sets_target)
    mean_games = float(np.mean(total_games))

    return {
        'p1_match_win_prob':      round(float(p1_match_wins / iterations), 3),
        'p2_match_win_prob':      round(float(1.0 - (p1_match_wins / iterations)), 3),
        'p1_first_set_win_prob':  round(float(np.mean(first_set_winners == 1)), 3),
        'p2_first_set_win_prob':  round(float(np.mean(first_set_winners == 2)), 3),
        'expected_total_games':   round(mean_games, 1),

        # Over/Under probabilities for common lines
        'over_20_5_prob':  round(float(np.mean(total_games > 20.5)), 3),
        'over_21_5_prob':  round(float(np.mean(total_games > 21.5)), 3),
        'over_22_5_prob':  round(float(np.mean(total_games > 22.5)), 3),
        'over_23_5_prob':  round(float(np.mean(total_games > 23.5)), 3),
        'over_24_5_prob':  round(float(np.mean(total_games > 24.5)), 3),
        'under_20_5_prob': round(float(np.mean(total_games < 20.5)), 3),
        'under_21_5_prob': round(float(np.mean(total_games < 21.5)), 3),
        'under_22_5_prob': round(float(np.mean(total_games < 22.5)), 3),
        'under_23_5_prob': round(float(np.mean(total_games < 23.5)), 3),

        # Set score probabilities
        'p1_wins_2_0_prob': round(float(np.mean((p1_sets >= sets_target) & (p2_sets == 0))), 3),
        'p1_wins_2_1_prob': round(float(np.mean((p1_sets >= sets_target) & (p2_sets == 1))), 3) if sets_target == 2 else 0.0,

        # Raw distribution for custom line analysis
        'raw_game_distribution': total_games.tolist(),

        # Diagnostic
        'p1_serve_point_prob':  round(p1_p, 4),
        'p2_serve_point_prob':  round(p2_p, 4),
        'p1_hold_game_prob':    round(p1_game_prob, 4),
        'p2_hold_game_prob':    round(p2_game_prob, 4),
        'sets_to_win':          sets_target,
    }


# ---------------------------------------------------------------------------
# CLI Test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Sinner vs Djokovic — Wimbledon semifinal example
    sinner = {
        'first_serve_pct':       0.63,
        'first_serve_win_pct':   0.76,
        'second_serve_win_pct':  0.54,
        'return_points_won_pct': 0.38,
    }
    djokovic = {
        'first_serve_pct':       0.65,
        'first_serve_win_pct':   0.73,
        'second_serve_win_pct':  0.55,
        'return_points_won_pct': 0.40,
    }

    result = simulate_match_monte_carlo(
        sinner, djokovic,
        tour='ATP', surface='Grass', tournament_name='Wimbledon',
        iterations=50000,
    )

    print("=== Sinner vs Djokovic -- Wimbledon (Grass, Bo5) ===")
    print(f"Sinner win:     {result['p1_match_win_prob']:.1%}")
    print(f"Djokovic win:   {result['p2_match_win_prob']:.1%}")
    print(f"Expected games: {result['expected_total_games']}")
    print(f"Over 22.5:      {result['over_22_5_prob']:.1%}")
    print(f"Under 22.5:     {result['under_22_5_prob']:.1%}")
    print(f"\nDiagnostic:")
    print(f"  Sinner serve point prob:   {result['p1_serve_point_prob']}")
    print(f"  Djokovic serve point prob: {result['p2_serve_point_prob']}")
    print(f"  Sinner hold prob:          {result['p1_hold_game_prob']:.1%}")
    print(f"  Djokovic hold prob:        {result['p2_hold_game_prob']:.1%}")
