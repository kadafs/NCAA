"""
surface_engine.py
=================
Surface and tour-specific modifiers for the tennis Markov model.

Optimized to secure complete log-odds mathematical boundaries and
prevent tournament string inference parsing collisions.

Design principles:
  1. SURFACE_MODIFIERS apply multiplicatively to raw serve rates BEFORE
     log-odds blending — NOT as additive point shifts (which break boundary
     integrity at the extremes of the talent spectrum).
  2. Tournament name resolution uses substring token matching, not set
     membership equality, to prevent string collision hard-court fallbacks
     (e.g., "Roland Garros" ≠ "French Open" in a set lookup).
"""

# ---------------------------------------------------------------------------
# Serve Dominance Multipliers: (tour, surface) -> float
# Applied strictly within log-odds space to preserve boundary integrity.
# > 1.0 = serve more dominant (fewer breaks, more tiebreaks)
# < 1.0 = returner more dominant (more breaks, shorter sets)
# ---------------------------------------------------------------------------
SURFACE_MODIFIERS = {
    # Calibrated against real Tennis-Data.co.uk distributions (2022-2026)
    # Target hold rates derived from observed mean games/set per surface:
    #   Grass Bo5: mean 37.9 games / 3.77 sets = 10.05 games/set -> ~83% hold
    #   Hard:      baseline 80% hold (model anchor)
    #   Clay:      ~76-77% hold (more breaks, more upsets)
    #
    # Formula: modifier = target_odds / baseline_odds (in log-odds space)
    #   ATP Grass: target p=0.652 -> odds=1.874 / baseline 1.725 = 1.087 -> 1.09
    #   ATP Clay:  target p=0.610 -> odds=1.564 / baseline 1.725 = 0.907 -> 0.90
    #   WTA Grass: target p=0.565 -> odds=1.299 / baseline 1.218 = 1.067 -> 1.07
    #   WTA Clay:  target p=0.535 -> odds=1.151 / baseline 1.218 = 0.945 -> 0.94
    ('ATP', 'Hard'):  1.00,   # Neutral baseline
    ('ATP', 'Clay'):  0.90,   # Slower surface: more breaks, more upsets
    ('ATP', 'Grass'): 1.09,   # Fast surface: slight serve boost (was 1.20 -> over-inflated)
    ('WTA', 'Hard'):  1.00,   # Neutral baseline
    ('WTA', 'Clay'):  0.94,   # Moderate returner advantage on clay
    ('WTA', 'Grass'): 1.07,   # Flat-ball hitters gain slight edge (was 1.15 -> over-inflated)
}

# ---------------------------------------------------------------------------
# Baseline League Hold Rates (P(server wins a service game))
# Used as the log-odds blending anchor — game-level, not point-level.
# ---------------------------------------------------------------------------
LEAGUE_HOLD = {
    'ATP': 0.800,
    'WTA': 0.620,
}

# ---------------------------------------------------------------------------
# League Baseline Point-Win Probabilities
# Calibrated so _p_server_wins_game(p) == LEAGUE_HOLD[tour]:
#   ATP: p=0.633 -> hold=0.8002  (was 0.630 -> 0.7947, off by 0.005)
#   WTA: p=0.549 -> hold=0.6208  (was 0.540 -> 0.5990, off by 0.021)
# ---------------------------------------------------------------------------
LEAGUE_POINT_PROB = {
    'ATP': 0.633,
    'WTA': 0.549,
}

# ---------------------------------------------------------------------------
# Tournament Level Metadata — all lowercase for collision-safe matching
# ---------------------------------------------------------------------------

# Grand Slams (lowercase) — used in sets_to_win substring check
GRAND_SLAMS = {
    'australian open', 'french open', 'roland garros', 'wimbledon', 'us open',
}

# String token map: prevents multi-word text collisions.
# 'roland garros' is explicitly present to block the hard-court fallback bug
# (live scoreboards label it differently from historical sheets).
TOURNAMENT_SURFACES = {
    'australian open': 'Hard',
    'french open':     'Clay',
    'roland garros':   'Clay',   # Fix 2: explicit entry, blocks hard-court fallback
    'wimbledon':       'Grass',
    'us open':         'Hard',
    'miami open':      'Hard',
    'indian wells':    'Hard',
    'monte carlo':     'Clay',
    'madrid open':     'Clay',
    'rome':            'Clay',
    'canada masters':  'Hard',
    'toronto':         'Hard',   # Rogers Cup (ATP)
    'montreal':        'Hard',   # Rogers Cup alternate host
    'cincinnati':      'Hard',
    'shanghai':        'Hard',
    'paris':           'Hard',
    'dubai':           'Hard',
    'halle':           'Grass',
    "queen's club":    'Grass',
    "queen's":         'Grass',
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def get_surface_modifier(tour: str, surface: str) -> float:
    """Return serve dominance multiplier for (tour, surface) pair."""
    return SURFACE_MODIFIERS.get((tour, surface), 1.00)


def get_league_hold(tour: str) -> float:
    """Return baseline hold rate for the tour."""
    return LEAGUE_HOLD.get(tour, 0.72)


def get_league_point_prob(tour: str) -> float:
    """Return baseline point-win probability for the tour."""
    return LEAGUE_POINT_PROB.get(tour, 0.58)


def sets_to_win(tour: str, tournament_name: str) -> int:
    """
    Returns the number of sets required to win a match.
    WTA: always Best-of-3 (returns 2) — including Grand Slams.
    ATP: Best-of-3 for all events EXCEPT Grand Slams (returns 3).

    Uses substring matching (not set equality) so 'Roland Garros Grand Slam'
    is correctly identified as a Grand Slam.
    """
    if not tournament_name:
        return 2
    t_clean = tournament_name.lower().strip()
    if tour == 'ATP' and any(gs in t_clean for gs in GRAND_SLAMS):
        return 3
    return 2


def infer_surface(tournament_name: str) -> str:
    """
    Infer court surface from tournament name tokens.

    Prevents silent hard-court fallbacks on major clay/grass venues.
    Loops through TOURNAMENT_SURFACES token map rather than using set
    membership so 'Roland Garros' and 'French Open' both resolve to Clay.
    """
    if not tournament_name:
        return 'Hard'
    t_clean = tournament_name.lower().strip()
    for token, surface in TOURNAMENT_SURFACES.items():
        if token in t_clean:
            return surface
    return 'Hard'   # safe default
