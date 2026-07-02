"""
ground_factors.py
=================
Ground dimension and dew factor modifiers for T20 cricket simulation.

Ground factor drives a run-scaling multiplier (analogous to park_factors.py in MLB).

Key inputs:
  - Average first-innings score at the ground
  - Boundary rope distance (small = more 6s)
  - Dew factor (evening matches in Asia/subcontinent benefit batting team in 2nd innings)
  - Pitch surface type (batting-friendly / balanced / bowling-friendly)
"""

# ---------------------------------------------------------------------------
# Ground Factors Dictionary
# Ground factor = (avg_score_at_venue / league_avg_score)
# League average T20 first innings: ~165 runs
# ---------------------------------------------------------------------------
LEAGUE_AVG_SCORE = 165.0

GROUND_FACTORS = {
    # Format: 'Ground Name': {'factor': float, 'dew': bool, 'pitch': str, 'avg_score': int}

    # IPL venues
    'Wankhede Stadium':             {'factor': 1.08, 'dew': True,  'pitch': 'batting',  'avg_score': 178},
    'M. Chinnaswamy Stadium':       {'factor': 1.12, 'dew': True,  'pitch': 'batting',  'avg_score': 185},
    'Eden Gardens':                 {'factor': 0.98, 'dew': True,  'pitch': 'balanced', 'avg_score': 162},
    'Arun Jaitley Stadium':         {'factor': 1.03, 'dew': True,  'pitch': 'batting',  'avg_score': 170},
    'MA Chidambaram Stadium':       {'factor': 0.94, 'dew': True,  'pitch': 'bowling',  'avg_score': 155},
    'Narendra Modi Stadium':        {'factor': 1.00, 'dew': True,  'pitch': 'balanced', 'avg_score': 165},
    'Rajiv Gandhi Intl Stadium':    {'factor': 1.05, 'dew': True,  'pitch': 'batting',  'avg_score': 173},
    'Punjab Cricket Association':   {'factor': 1.07, 'dew': False, 'pitch': 'batting',  'avg_score': 176},
    'DY Patil Sports Academy':      {'factor': 1.06, 'dew': True,  'pitch': 'batting',  'avg_score': 175},

    # BBL venues (Australia)
    'Melbourne Cricket Ground':     {'factor': 1.00, 'dew': False, 'pitch': 'balanced', 'avg_score': 165},
    'Adelaide Oval':                {'factor': 1.04, 'dew': False, 'pitch': 'batting',  'avg_score': 172},
    'Sydney Cricket Ground':        {'factor': 0.97, 'dew': False, 'pitch': 'balanced', 'avg_score': 160},
    'Perth Stadium':                {'factor': 1.02, 'dew': False, 'pitch': 'batting',  'avg_score': 168},
    'Gabba':                        {'factor': 0.98, 'dew': False, 'pitch': 'balanced', 'avg_score': 162},
    'Manuka Oval':                  {'factor': 1.01, 'dew': False, 'pitch': 'batting',  'avg_score': 167},

    # The Hundred venues (UK)
    "Lord's":                       {'factor': 0.93, 'dew': False, 'pitch': 'bowling',  'avg_score': 153},
    'The Oval':                     {'factor': 0.96, 'dew': False, 'pitch': 'balanced', 'avg_score': 158},
    'Edgbaston':                    {'factor': 1.02, 'dew': False, 'pitch': 'batting',  'avg_score': 168},
    'Headingley':                   {'factor': 0.98, 'dew': False, 'pitch': 'balanced', 'avg_score': 162},
    'Emirates Old Trafford':        {'factor': 0.95, 'dew': False, 'pitch': 'bowling',  'avg_score': 157},
    'Sophia Gardens':               {'factor': 0.97, 'dew': False, 'pitch': 'balanced', 'avg_score': 160},
    'Utilita Bowl':                 {'factor': 0.96, 'dew': False, 'pitch': 'bowling',  'avg_score': 158},
    'Trent Bridge':                 {'factor': 1.01, 'dew': False, 'pitch': 'batting',  'avg_score': 166},

    # PSL venues (Pakistan)
    'National Stadium Karachi':     {'factor': 1.05, 'dew': True,  'pitch': 'batting',  'avg_score': 173},
    'Gaddafi Stadium':              {'factor': 1.00, 'dew': True,  'pitch': 'balanced', 'avg_score': 165},
    'Rawalpindi Cricket Stadium':   {'factor': 1.03, 'dew': False, 'pitch': 'batting',  'avg_score': 170},

    # International T20 venues
    'SuperSport Park':              {'factor': 1.06, 'dew': False, 'pitch': 'batting',  'avg_score': 175},
    'Newlands':                     {'factor': 0.96, 'dew': False, 'pitch': 'bowling',  'avg_score': 158},
    'Kensington Oval':              {'factor': 1.03, 'dew': True,  'pitch': 'batting',  'avg_score': 170},
    'Duckworth-Lewis':              {'factor': 1.00, 'dew': False, 'pitch': 'balanced', 'avg_score': 165},
}

# ---------------------------------------------------------------------------
# Dew Factor Modifier
# When dew is present, the ball becomes harder to grip for bowlers in the 2nd innings
# Batting team chasing benefits by ~6-8% in run rate
# ---------------------------------------------------------------------------
DEW_FACTOR_MODIFIER = 1.07   # 7% scoring uplift for chasing team when dew present


def get_ground_factor(venue_name: str) -> dict:
    """
    Look up ground factor by venue name. Falls back to fuzzy match, then neutral.

    Returns dict with: factor, dew, pitch, avg_score
    """
    # Exact match
    if venue_name in GROUND_FACTORS:
        return GROUND_FACTORS[venue_name]

    # Fuzzy match (partial name)
    venue_lower = venue_name.lower()
    for name, data in GROUND_FACTORS.items():
        if any(part in venue_lower for part in name.lower().split()):
            return data

    # Default neutral
    return {'factor': 1.00, 'dew': False, 'pitch': 'balanced', 'avg_score': int(LEAGUE_AVG_SCORE)}


def get_powerplay_factor(venue_name: str) -> float:
    """
    Derive a powerplay-specific factor from ground data.
    Small grounds inflate powerplay scoring more than overall factor.
    """
    data = get_ground_factor(venue_name)
    base = data['factor']
    # Powerplay amplification: batting-friendly grounds score +3% more in PP
    if data['pitch'] == 'batting':
        return round(base * 1.03, 3)
    elif data['pitch'] == 'bowling':
        return round(base * 0.97, 3)
    return round(base, 3)
