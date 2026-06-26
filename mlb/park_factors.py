"""
Static Park Factor Matrix for MLB Stadiums.
Values represent a multiplier for total runs scored (e.g. 1.15 = +15% runs, 0.92 = -8% runs).
These are based on multi-year rolling averages of Statcast Park Factors.
"""

MLB_PARK_FACTORS = {
    # Extreme Hitter / Exceptions
    "Las Vegas Ballpark": 1.250,
    "Coors Field": 1.154,
    "Sutter Health Park": 1.133,
    "Great American Ball Park": 1.108,
    
    # Hitter Friendly
    "Fenway Park": 1.051,
    "Kauffman Stadium": 1.047,
    "Citizens Bank Park": 1.032,
    "Chase Field": 1.029,
    "Daikin Park": 1.026,
    "Minute Maid Park": 1.026, # alias
    "Nationals Park": 1.017,
    "Oriole Park at Camden Yards": 1.010,
    
    # Near Neutral
    "Target Field": 1.004,
    "Globe Life Field": 1.003,
    "Yankee Stadium": 0.994,
    "American Family Field": 0.992,
    "Truist Park": 0.989,
    "Rogers Centre": 0.988,
    "Progressive Field": 0.988,
    "Angel Stadium": 0.984,
    "Wrigley Field": 0.982,
    "UNIQLO Field at Dodger Stadium": 0.979,
    "Dodger Stadium": 0.979, # alias
    "Guaranteed Rate Field": 0.976,
    
    # Pitcher Friendly
    "PNC Park": 0.977,
    "loanDepot park": 0.972,
    "Tropicana Field": 0.968,
    "Comerica Park": 0.964,
    "Citi Field": 0.957,
    "Oracle Park": 0.955,
    "Busch Stadium": 0.947,
    "Petco Park": 0.923,
    
    # Extreme Pitcher Friendly
    "T-Mobile Park": 0.898
}

import os
import json

_cached_dynamic_pf = None
_dynamic_pf_loaded = False

def get_park_factor(venue_name: str) -> float:
    """
    Returns the Run Park Factor multiplier for the given stadium.
    If the stadium is not found (e.g. MiLB parks, international games),
    it defaults to 1.00 (Neutral).
    """
    global _cached_dynamic_pf, _dynamic_pf_loaded
    
    if not _dynamic_pf_loaded:
        try:
            json_path = os.path.join(os.path.dirname(__file__), 'Current_Blended_F5_PF.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    _cached_dynamic_pf = json.load(f)
        except Exception as e:
            print(f"Warning: Could not load Current_Blended_F5_PF.json: {e}")
        _dynamic_pf_loaded = True

    # Check dynamic JSON first
    if _cached_dynamic_pf:
        for park, data in _cached_dynamic_pf.items():
            if park.lower() in venue_name.lower():
                return data.get("blended", 1.00) if isinstance(data, dict) else data
                
    # Fallback to static dictionary
    for park, factor in MLB_PARK_FACTORS.items():
        if park.lower() in venue_name.lower():
            return factor
            
    return 1.00

def get_park_factor_details(venue_name: str) -> dict:
    """
    Returns a dict with 'blended', 'static', and 'realized' keys for the given venue.
    If the JSON is not available or venue is not found, returns a dict with all values set to the static factor.
    """
    static_pf = get_park_factor(venue_name)
    
    global _cached_dynamic_pf, _dynamic_pf_loaded
    
    if not _dynamic_pf_loaded:
        try:
            json_path = os.path.join(os.path.dirname(__file__), 'Current_Blended_F5_PF.json')
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    _cached_dynamic_pf = json.load(f)
        except Exception as e:
            pass
        _dynamic_pf_loaded = True
        
    if _cached_dynamic_pf:
        for park, data in _cached_dynamic_pf.items():
            if park.lower() in venue_name.lower():
                if isinstance(data, dict):
                    return data
                else:
                    return {"blended": data, "static": static_pf, "realized": static_pf}
                    
    return {"blended": static_pf, "static": static_pf, "realized": static_pf}
