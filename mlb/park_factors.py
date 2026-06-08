"""
Static Park Factor Matrix for MLB Stadiums.
Values represent a multiplier for total runs scored (e.g. 1.15 = +15% runs, 0.92 = -8% runs).
These are based on multi-year rolling averages of Statcast Park Factors.
"""

MLB_PARK_FACTORS = {
    # Hitter Friendly
    "Coors Field": 1.15,
    "Great American Ball Park": 1.12,
    "Fenway Park": 1.08,
    "Kauffman Stadium": 1.05,
    "Chase Field": 1.02,
    "Citizens Bank Park": 1.02,
    "Truist Park": 1.01,
    "Globe Life Field": 1.01,
    "Progressive Field": 1.01,
    
    # Neutral
    "UNIQLO Field at Dodger Stadium": 1.00,  # formerly Dodger Stadium
    "Dodger Stadium": 1.00,                   # legacy name alias
    "Daikin Park": 1.00,                      # formerly Minute Maid Park
    "Minute Maid Park": 1.00,                 # legacy name alias
    "Rogers Centre": 1.00,
    "American Family Field": 1.00,
    
    # Slight Pitcher Friendly
    "Oriole Park at Camden Yards": 0.99,
    "Target Field": 0.99,
    "Guaranteed Rate Field": 0.99,
    "Yankee Stadium": 0.99,
    "Nationals Park": 0.98,
    "Comerica Park": 0.98,
    "Wrigley Field": 0.98,
    "Angel Stadium": 0.98,
    
    # Pitcher Friendly
    "Tropicana Field": 0.97,
    "loanDepot park": 0.97,
    "Oracle Park": 0.96,
    "Busch Stadium": 0.96,
    "PNC Park": 0.95,
    "Oakland Coliseum": 0.94,
    "Citi Field": 0.94,
    "Petco Park": 0.94,
    "T-Mobile Park": 0.92
}

def get_park_factor(venue_name: str) -> float:
    """
    Returns the Run Park Factor multiplier for the given stadium.
    If the stadium is not found (e.g. MiLB parks, international games),
    it defaults to 1.00 (Neutral).
    """
    # Simple fuzzy match in case of slight name differences
    for park, factor in MLB_PARK_FACTORS.items():
        if park.lower() in venue_name.lower():
            return factor
            
    return 1.00
