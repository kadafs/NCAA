"""
npb/park_factors.py
Static park factor table for the 12 NPB stadiums.
NPB has many roofed stadiums (domes) which neutralises weather effects.
"""

# NPB Park Factors: >1.0 = hitter-friendly, <1.0 = pitcher-friendly
# Data based on historical run environments.
NPB_PARK_DATA = {
    # Central League
    'Yomiuri Giants':        {'pf': 1.05, 'venue': 'Tokyo Dome',              'roofed': True},
    'Yakult Swallows':       {'pf': 1.08, 'venue': 'Meiji Jingu Stadium',     'roofed': False},
    'DeNA BayStars':         {'pf': 1.04, 'venue': 'Yokohama Stadium',        'roofed': False},
    'Hanshin Tigers':        {'pf': 0.94, 'venue': 'Koshien Stadium',         'roofed': False},
    'Hiroshima Carp':        {'pf': 0.98, 'venue': 'Mazda Stadium',           'roofed': False},
    'Chunichi Dragons':      {'pf': 0.91, 'venue': 'Vantelin Dome Nagoya',    'roofed': True},
    
    # Pacific League
    'Orix Buffaloes':        {'pf': 0.95, 'venue': 'Kyocera Dome Osaka',      'roofed': True},
    'Lotte Marines':         {'pf': 0.97, 'venue': 'ZOZO Marine Stadium',     'roofed': False},
    'SoftBank Hawks':        {'pf': 1.01, 'venue': 'PayPay Dome',             'roofed': True},
    'Rakuten Eagles':        {'pf': 0.96, 'venue': 'Rakuten Mobile Park',     'roofed': False},
    'Seibu Lions':           {'pf': 0.95, 'venue': 'Belluna Dome',            'roofed': True}, # Technically open-sided but covered
    'Nippon-Ham Fighters':   {'pf': 0.97, 'venue': 'Es Con Field Hokkaido',   'roofed': True},
}

DEFAULT_PF = 0.98  # NPB is generally a pitcher-friendly league

def get_npb_park_factor(home_team: str) -> tuple[float, bool]:
    if home_team in NPB_PARK_DATA:
        d = NPB_PARK_DATA[home_team]
        return d['pf'], d['roofed']
        
    # Fuzzy match
    home_lower = home_team.lower()
    for team, d in NPB_PARK_DATA.items():
        if any(part in home_lower for part in team.lower().split() if len(part) > 3):
            return d['pf'], d['roofed']
            
    return DEFAULT_PF, False
