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


# League-average point-win probabilities (probability that SERVER wins a point).
# These are the point-level values that produce the observed league hold rates:
#   ATP: p=0.630 -> p_server_wins_game = ~0.800 (80% hold rate)
#   WTA: p=0.540 -> p_server_wins_game = ~0.620 (62% hold rate)
LEAGUE_POINT_PROB = {
    'ATP': 0.630,
    'WTA': 0.540,
}

# Surface adjustments: ADDITIVE point-probability shifts.
# Applied after the log-odds blend so they don't inflate raw serve stats.
SURFACE_POINT_ADJUSTMENTS = {
    ('ATP', 'Hard'):  0.000,
    ('ATP', 'Clay'): -0.030,   # slower court: serve loses ~3 pp
    ('ATP', 'Grass'): 0.040,   # faster court: serve gains ~4 pp
    ('WTA', 'Hard'):  0.000,
    ('WTA', 'Clay'): -0.020,
    ('WTA', 'Grass'): 0.025,
}


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
    # Server's raw point-win rate from their own serve statistics
    raw_serve = server_fsp * server_fsw + (1.0 - server_fsp) * server_ssw

    # Returner's implied point-win rate for the SERVER:
    # returner_rpw = % of return points WON by returner -> server wins (1 - rpw)
    returner_estimate = max(0.01, min(0.99, 1.0 - returner_rpw))

    # League baseline at point level (not hold level)
    league_point = LEAGUE_POINT_PROB.get(tour, 0.630)

    # Log-odds blend of both estimates against league baseline
    p_base = log_odds_blend(raw_serve, returner_estimate, league_point)

    # Apply surface as additive point-probability shift
    surface_adj = SURFACE_POINT_ADJUSTMENTS.get((tour, surface), 0.00)
    return max(0.01, min(0.99, p_base + surface_adj))


# ---------------------------------------------------------------------------
# Tiebreak Simulation
# ---------------------------------------------------------------------------

def simulate_tiebreak_vectorized(
    p_p1_serve: float,
    p_p2_serve: float,
    num_active: int,
) -> np.ndarray:
    """
    Simulates a standard 7-point tennis tiebreak for a vector of active games.

    Serving sequence: P1 serves point 1, then P2 serves 2-3, P1 serves 4-5, etc.
    Mathematically: point n → server is P2 if ((n+1)//2) % 2 == 1, else P1.

    Parameters
    ----------
    p_p1_serve : P(P1 wins point when serving)
    p_p2_serve : P(P2 wins point when serving)
    num_active : number of active tiebreaks to simulate

    Returns
    -------
    np.ndarray[bool] : True where Player 1 won the tiebreak
    """
    p1_pts = np.zeros(num_active, dtype=np.int32)
    p2_pts = np.zeros(num_active, dtype=np.int32)
    total_pts = np.zeros(num_active, dtype=np.int32)
    tb_active = np.ones(num_active, dtype=bool)

    while np.any(tb_active):
        idx = np.where(tb_active)[0]

        # Server determination: P2 serves if ((total_points + 1) // 2) is odd
        is_p2_serving = ((total_pts[idx] + 1) // 2) % 2 == 1
        p_win = np.where(is_p2_serving, 1.0 - p_p2_serve, p_p1_serve)

        r = np.random.rand(len(idx))
        p1_won = r < p_win

        p1_pts[idx[p1_won]] += 1
        p2_pts[idx[~p1_won]] += 1
        total_pts[idx] += 1

        # Must reach 7+ and lead by 2+
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
                p1_won_tb = simulate_tiebreak_vectorized(p1_p, p2_p, len(tb_sub))

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
