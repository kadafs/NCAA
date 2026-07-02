"""
surface_engine.py
=================
Surface and tour-specific modifiers for the tennis Markov model.

Serve dominance multipliers by (tour, surface):
  > 1.0 = serve more dominant (fewer breaks, more tiebreaks -> higher game totals)
  < 1.0 = returner more dominant (more breaks, shorter sets -> lower game totals)

League hold baselines:
  ATP: ~0.80 (servers hold ~80% of games)
  WTA: ~0.62 (servers hold ~62% of games -- far more break-heavy)
"""

# ---------------------------------------------------------------------------
# Serve Dominance Multipliers: (tour, surface) -> float
# ---------------------------------------------------------------------------
SURFACE_MODIFIERS = {
    ('ATP', 'Hard'):  1.00,   # Neutral baseline
    ('ATP', 'Clay'):  0.85,   # Slower surface: serve loses dominance, more upsets
    ('ATP', 'Grass'): 1.20,   # Fast surface: serve-dominant, tiebreaks common
    ('WTA', 'Hard'):  1.00,   # Neutral baseline
    ('WTA', 'Clay'):  0.92,   # Moderate returner advantage on clay
    ('WTA', 'Grass'): 1.15,   # Fast courts amplify flat-ball hitters
}

# ---------------------------------------------------------------------------
# Baseline League Hold Rates (P(server wins a service game))
# ---------------------------------------------------------------------------
LEAGUE_HOLD = {
    'ATP': 0.800,
    'WTA': 0.620,
}

# ---------------------------------------------------------------------------
# Tournament Level Metadata
# ---------------------------------------------------------------------------
GRAND_SLAMS = {
    'Australian Open', 'French Open', 'Roland Garros',
    'Wimbledon', 'US Open',
}

TOURNAMENT_SURFACES = {
    'Australian Open':  'Hard',
    'French Open':      'Clay',
    'Roland Garros':    'Clay',
    'Wimbledon':        'Grass',
    'US Open':          'Hard',
    'Miami Open':       'Hard',
    'Indian Wells':     'Hard',
    'Monte Carlo':      'Clay',
    'Madrid Open':      'Clay',
    'Rome':             'Clay',
    'Canada Masters':   'Hard',
    'Cincinnati':       'Hard',
    'Shanghai':         'Hard',
    'Paris':            'Hard',
    'Dubai':            'Hard',
    'Halle':            'Grass',
    "Queen's Club":     'Grass',
    "Queen's":          'Grass',
}


def get_surface_modifier(tour: str, surface: str) -> float:
    """Return serve dominance multiplier for (tour, surface) pair."""
    return SURFACE_MODIFIERS.get((tour, surface), 1.00)


def get_league_hold(tour: str) -> float:
    """Return baseline hold rate for the tour."""
    return LEAGUE_HOLD.get(tour, 0.72)


def sets_to_win(tour: str, tournament_name: str) -> int:
    """
    Returns the number of sets required to win a match.
    WTA: always Best-of-3 (returns 2) -- including Grand Slams.
    ATP: Best-of-3 for all events EXCEPT Grand Slams (returns 3).
    """
    if tour == 'ATP' and tournament_name in GRAND_SLAMS:
        return 3
    return 2


def infer_surface(tournament_name: str) -> str:
    """Attempt to infer court surface from tournament name."""
    for name, surface in TOURNAMENT_SURFACES.items():
        if name.lower() in tournament_name.lower():
            return surface
    return 'Hard'  # Default to hard court
