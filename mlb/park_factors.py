"""
Static Park Factor Matrix for MLB, AAA, and AA Stadiums.
Values represent a multiplier for total runs scored (e.g. 1.15 = +15% runs, 0.92 = -8% runs).
MLB values based on multi-year rolling averages of Statcast Park Factors.
MiLB values based on historical run-scoring data and altitude/climate factors.
"""

MLB_PARK_FACTORS = {
    # ── MLB ──────────────────────────────────────────────────────────────────

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
    "T-Mobile Park": 0.898,

    # ── AAA — Pacific Coast League (PCL) — Hitter Friendly ───────────────────
    # High altitude, heat, and dry air inflate run scoring significantly
    "Constellation Field":              1.185,  # Sugar Land Space Cowboys (Houston suburb, heat)
    "Greater Nevada Field":             1.180,  # Reno Aces (altitude ~4,500ft + heat)
    "Chickasaw Bricktown Ballpark":     1.160,  # OKC Comets (hot/dry climate)
    "Isotopes Park":                    1.150,  # Albuquerque Isotopes (altitude ~5,300ft — extreme)
    "Hodgetown":                        1.140,  # Amarillo Sod Poodles (heat/dry)
    "Principal Park":                   1.110,  # Iowa Cubs (hitter-friendly dimensions)
    "Momentum Bank Ballpark":           1.100,  # Midland RockHounds (TX heat)
    "Round Rock":                       1.095,  # Dell Diamond (suburban TX)
    "Toyota Field":                     1.070,  # Rocket City Trash Pandas (AL heat)

    # ── AAA — International League (IL) — Closer to Neutral ─────────────────
    "Truist Field":                     1.050,  # Charlotte Knights
    "Louisville Slugger Field":         1.040,  # Louisville Bats
    "Victory Field":                    1.030,  # Indianapolis Indians
    "Harbor Park":                      1.025,  # Norfolk Tides
    "Polar Park":                       1.020,  # Worcester Red Sox
    "Louisville Slugger Field":         1.015,  # Louisville Bats (alias)
    "Gwinnett Field":                   1.010,  # Gwinnett Stripers
    "Sahlen Field":                     0.995,  # Buffalo Bisons (wind, cold)
    "Coca-Cola Park":                   0.990,  # Lehigh Valley IronPigs
    "VyStar Ballpark":                  0.988,  # Jacksonville Jumbo Shrimp
    "Vystar Ballpark":                  0.988,  # alias (lowercase v)
    "Durham Bulls Athletic Park":       0.985,  # Durham Bulls
    "Dunkin' Park":                     0.982,  # Hartford Yard Goats (alternate name)
    "AutoZone Park":                    1.015,  # Memphis Redbirds

    # ── AA — Eastern League (EL) ─────────────────────────────────────────────
    "Polar Park":                       1.020,  # (also AAA alias)
    "Delta Dental Stadium":             1.005,  # Portland Sea Dogs
    "TD Bank Ballpark":                 1.000,  # Somerset Patriots
    "Dunkin' Park":                     0.990,  # Hartford Yard Goats
    "UPMC Park":                        0.985,  # Erie SeaWolves
    "7 17 Credit Union Park":           0.980,  # Akron RubberDucks (officially "Canal Park" area)
    "Peoples Natural Gas Field":        0.978,  # Altoona Curve
    "Binghamton Rumble Ponies":         0.982,  # Mirabito Stadium (alias fallback)
    "Harrisburg Senators":              0.985,  # FNB Field (alias fallback)
    "Reading Fightin Phils":            1.000,  # FirstEnergy Stadium (alias fallback)

    # ── AA — Southern League (SL) ────────────────────────────────────────────
    "Covenant Health Park":             1.005,  # Knoxville Smokies
    "Synovus Park":                     1.015,  # Columbus Clingstones
    "Blue Wahoos Stadium":              0.988,  # Pensacola Blue Wahoos
    "Toyota Field":                     1.040,  # Rocket City Trash Pandas (also PCL alias)
    "Riverwalk Stadium":                1.020,  # Montgomery Biscuits (Riverwalk alias)
    "Blue Wahoos":                      0.988,  # alias

    # ── AA — Texas League (TL) ───────────────────────────────────────────────
    "Whataburger Field":                1.080,  # Corpus Christi Hooks (heat/coastal)
    "ONEOK Field":                      1.070,  # Tulsa Drillers
    "Hodgetown":                        1.140,  # Amarillo Sod Poodles (already above, alias OK)
    "Momentum Bank Ballpark":           1.100,  # Midland RockHounds (already above)
    "Equity Bank Park":                 1.065,  # Wichita Wind Surge
    "Arvest Ballpark":                  1.055,  # Northwest Arkansas Naturals
    "Dickey-Stephens Park":             1.045,  # Arkansas Travelers
    "Nelson Wolff Stadium":             1.090,  # San Antonio Missions (TX heat)
    "Dr Pepper Ballpark":               1.075,  # Frisco RoughRiders (TX heat)
    "Springfield Cardinals":            1.035,  # Hammons Field (alias fallback)
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
