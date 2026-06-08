"""
stadium_config.py
=================
Static registry of MLB stadium roof types.
Used by weather_f5.py to determine whether to apply outdoor weather modifiers.
"""

# Permanent domes: always indoor, never affected by weather
PERMANENT_DOMES = {
    "Tropicana Field",      # Tampa Bay Rays
}

# Retractable roofs: may be open or closed depending on conditions
RETRACTABLE_ROOFS = {
    "Chase Field",               # Arizona Diamondbacks
    "Daikin Park",               # Houston Astros  (formerly Minute Maid Park)
    "loanDepot park",            # Miami Marlins
    "American Family Field",     # Milwaukee Brewers
    "T-Mobile Park",             # Seattle Mariners
    "Globe Life Field",          # Texas Rangers
    "Rogers Centre",             # Toronto Blue Jays
}

# Indoor baseline environment when roof is closed or dome
INDOOR_TEMP   = 72   # °F — standard controlled temperature
INDOOR_WIND   = 0    # MPH — no wind indoors

def get_roof_type(venue_name: str) -> str:
    """
    Returns 'dome', 'retractable', or 'open' for a given venue name.
    Uses substring matching to handle minor naming differences.
    """
    venue_lower = venue_name.lower()
    for dome in PERMANENT_DOMES:
        if dome.lower() in venue_lower:
            return 'dome'
    for roof in RETRACTABLE_ROOFS:
        if roof.lower() in venue_lower:
            return 'retractable'
    return 'open'
