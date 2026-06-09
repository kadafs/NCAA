"""
kbo/park_factors.py
Static park factor table for the 10 KBO stadiums (2024-2026 rolling average).
Roof status determines weather modifier eligibility.
Sources: Baseball-Reference KBO park factors, historical run environment data.
"""

# KBO Park Factors: values > 1.0 = hitter-friendly, < 1.0 = pitcher-friendly
# Format: 'Team Name': {'pf': float, 'venue': str, 'roofed': bool}
KBO_PARK_DATA = {
    'Doosan Bears':     {'pf': 1.03, 'venue': 'Jamsil Baseball Stadium',    'roofed': False},
    'LG Twins':         {'pf': 1.03, 'venue': 'Jamsil Baseball Stadium',    'roofed': False},
    'Kia Tigers':       {'pf': 0.98, 'venue': 'Gwangju-Kia Champions Field','roofed': False},
    'Samsung Lions':    {'pf': 0.97, 'venue': 'Daegu Samsung Lions Park',   'roofed': False},
    'Lotte Giants':     {'pf': 1.01, 'venue': 'Sajik Baseball Stadium',     'roofed': False},
    'NC Dinos':         {'pf': 0.99, 'venue': 'Changwon NC Park',           'roofed': False},
    'SSG Landers':      {'pf': 0.98, 'venue': 'Incheon SSG Landers Field',  'roofed': False},
    'Kiwoom Heroes':    {'pf': 1.02, 'venue': 'Gocheok Sky Dome',           'roofed': True},
    'KT Wiz':           {'pf': 1.00, 'venue': 'Suwon KT Wiz Park',         'roofed': False},
    'Hanwha Eagles':    {'pf': 1.01, 'venue': 'Hanwha Life Eagles Park',    'roofed': False},
}

# Fallback for unknown venues
DEFAULT_PF = 1.00

def get_kbo_park_factor(home_team: str) -> tuple[float, bool]:
    """
    Returns (park_factor, is_roofed) for the given KBO home team name.
    Performs fuzzy matching to handle minor name variations.
    """
    # Direct lookup first
    if home_team in KBO_PARK_DATA:
        data = KBO_PARK_DATA[home_team]
        return data['pf'], data['roofed']
    
    # Fuzzy: check if team name appears in any key
    home_lower = home_team.lower()
    for team, data in KBO_PARK_DATA.items():
        if any(part in home_lower for part in team.lower().split()):
            return data['pf'], data['roofed']
    
    print(f"  [KBO PF] Unknown home team '{home_team}', using default PF={DEFAULT_PF}")
    return DEFAULT_PF, False


if __name__ == '__main__':
    print("KBO Park Factor Table")
    print(f"{'Team':<25} {'PF':>5}  {'Venue':<35} {'Roofed'}")
    print("-" * 80)
    for team, d in KBO_PARK_DATA.items():
        print(f"{team:<25} {d['pf']:>5.2f}  {d['venue']:<35} {'Yes' if d['roofed'] else 'No'}")
