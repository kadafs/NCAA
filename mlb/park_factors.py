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


    # ── AAA — Empirically calibrated from 5,850 real games (2024 + 2025 + 2026) ──
    # League avg F5: 6.197 runs/game. 3-year baseline neutralises team quality confound.
    # Venue names match statsapi exactly; historical aliases included for 2024/2025 seasons.

    # Hitter parks (altitude driven)
    "Isotopes Park":                        1.317,  # Albuquerque (5,300ft altitude) — consistent across 3 yrs
    "Southwest University Park":            1.286,  # El Paso (~3,700ft altitude)
    "Las Vegas Ballpark":                   1.285,  # Las Vegas Aviators (1-yr was 1.516 — team quality confound)
    "Greater Nevada Field":                 1.230,  # Reno Aces (~4,500ft altitude) — stronger than 1-yr
    "The Ballpark at America First Square": 1.221,  # Salt Lake Bees (~4,200ft altitude)
    "Smith's Ballpark":                     1.039,  # Salt Lake (historic name used 2024/2025)
    "America First Field":                  1.221,  # Salt Lake alias
    "CHS Field":                            1.136,  # St. Paul Saints

    # Mild hitter parks
    "Truist Field":                         1.109,  # Charlotte Knights
    "Principal Park":                       1.075,  # Iowa Cubs
    "NBT Bank Stadium":                     1.032,  # Syracuse Mets

    # Near neutral
    "Louisville Slugger Field":             1.022,  # Louisville Bats (1-yr was 1.174 — 2026 outlier)
    "Werner Park":                          1.011,  # Omaha Storm Chasers
    "Polar Park":                           1.010,  # Worcester Red Sox — neutral over 3 yrs (was 0.932)
    "PNC Field":                            1.003,  # Scranton/WB RailRiders — neutral (was 0.782!)
    "Cheney Stadium":                       1.002,  # Tacoma Rainiers — neutral over 3 yrs (was 0.843)
    "ESL Ballpark":                         0.992,  # Rochester Red Wings (2026 name)
    "Innovative Field":                     0.946,  # Rochester (historic name used 2024/2025)
    "Chickasaw Bricktown Ballpark":         0.980,  # OKC Comets — confirmed neutral across 3 yrs
    "Huntington Park":                      0.972,  # Columbus Clippers

    # Pitcher-friendly
    "AutoZone Park":                        0.956,  # Memphis Redbirds
    "Coca-Cola Park":                       0.918,  # Lehigh Valley IronPigs
    "Dell Diamond":                         0.917,  # Round Rock Express
    "Round Rock":                           0.917,  # alias
    "Harbor Park":                          0.910,  # Norfolk Tides
    "Durham Bulls Athletic Park":           0.904,  # Durham Bulls
    "Sahlen Field":                         0.891,  # Buffalo Bisons (1-yr was 0.759 — too extreme)
    "Victory Field":                        0.868,  # Indianapolis Indians
    "Fifth Third Field":                    0.865,  # Toledo Mud Hens
    "Sutter Health Park":                   0.857,  # Sacramento River Cats
    "First Horizon Park":                   0.844,  # Nashville Sounds
    "Toyota Field":                         0.844,  # Rocket City alias (AAA)
    "Coolray Field":                        0.842,  # Gwinnett (historic name used 2024/2025)

    # Strong pitcher parks
    "121 Financial Ballpark":              0.872,  # Jacksonville (historic name used 2024/2025)
    "Vystar Ballpark":                      0.813,  # Jacksonville Jumbo Shrimp (2026 name)
    "VyStar Ballpark":                      0.813,  # alias
    "Gwinnett Field":                       0.768,  # Gwinnett Stripers (2026 name)
    "Constellation Field":                  0.821,  # Sugar Land Space Cowboys — pitcher's park (3-yr confirmed)


    # ── AA — Empirically calibrated from 5,495 real games (2024 + 2025 + 2026) ──
    # League avg F5: 5.194 runs/game. 3-year baseline; historical name aliases included.

    # ── AA — Eastern League (EL) ─────────────────────────────────────────────
    "Hadlock Field":                    1.225,  # Portland Sea Dogs (historic name, 2024/2025)
    "DABOS Park":                       1.151,  # (EL) — hitter-friendly over 3 yrs
    "FirstEnergy Stadium":              1.140,  # Reading Fightin Phils
    "Reading Fightin Phils":            1.140,  # Reading alias
    "CarMax Park":                      1.119,  # (EL) — hitter-friendly over 3 yrs
    "UPMC Park":                        1.060,  # Erie SeaWolves (1-yr was 1.178 — outlier)
    "Prince George's Stadium":          1.009,  # Bowie Baysox — neutral over 3 yrs
    "Dunkin' Park":                     1.032,  # Hartford Yard Goats
    "Delta Dental Stadium":             1.027,  # Portland Sea Dogs (2026 name)
    "TD Bank Ballpark":                 1.032,  # Somerset Patriots
    "7 17 Credit Union Park":           1.000,  # Akron — only small sample in 3yr data
    "Peoples Natural Gas Field":        0.960,  # Altoona Curve — less pitcher-friendly over 3 yrs
    "Delta Dental Park":                0.988,  # Portland alternate name
    "The Diamond":                      0.921,  # Richmond Flying Squirrels
    "Riverfront Stadium":               0.873,  # (EL historic)
    "Mirabito Stadium":                 0.884,  # Binghamton Rumble Ponies
    "Binghamton Rumble Ponies":         0.884,  # alias
    "Canal Park":                       0.853,  # Akron RubberDucks (historic name)
    "FNB Field":                        0.865,  # Harrisburg Senators
    "Harrisburg Senators":              0.865,  # FNB Field alias

    # ── AA — Southern League (SL) ────────────────────────────────────────────
    "Route 66 Stadium":                 1.245,  # Springfield Cardinals — confirmed strong hitter's park
    "Springfield Cardinals":            1.245,  # alias
    "Hammons Field":                    1.074,  # Springfield / Hammons Field alternate name
    "AT&T Field":                       1.057,  # Chattanooga (historic name, 2024/2025)
    "Erlanger Park":                    1.043,  # Chattanooga Lookouts (2026 name)
    "Keesler Federal Park":             1.082,  # Biloxi Shuckers
    "Blue Wahoos Stadium":              0.958,  # Pensacola Blue Wahoos
    "Blue Wahoos":                      0.958,  # alias
    "Smokies Stadium":                  0.946,  # Knoxville (historic name)
    "Synovus Park":                     0.899,  # Columbus Clingstones — pitcher-friendly over 3 yrs
    "Toyota Field":                     0.910,  # Rocket City Trash Pandas (AA)
    "Montgomery Riverwalk Stadium":     0.904,  # Montgomery Biscuits (3-yr name)
    "Riverwalk Stadium":                0.904,  # alias
    "Mirabito Stadium":                 0.884,  # (also SL alias if needed)
    "Covenant Health Park":             0.848,  # Knoxville Smokies (2026 name)
    "Regions Field":                    0.833,  # Birmingham Barons — strong pitcher's park over 3 yrs
    "Trustmark Park":                   0.727,  # Mississippi Braves — extreme pitcher's park

    # ── AA — Texas League (TL) ───────────────────────────────────────────────
    "Hodgetown":                        1.323,  # Amarillo Sod Poodles — one of biggest hitter parks in MiLB
    "Equity Bank Park":                 1.265,  # Wichita Wind Surge — much higher than assumed
    "Arvest Ballpark":                  1.131,  # Northwest Arkansas Naturals — confirmed hitter's park over 3 yrs
    "Riders Field":                     1.080,  # Frisco RoughRiders (statsapi 2026 name)
    "Dr Pepper Ballpark":               1.080,  # Frisco alias
    "Momentum Bank Ballpark":           1.083,  # Midland RockHounds
    "ONEOK Field":                      1.086,  # Tulsa Drillers
    "Whataburger Field":                1.020,  # Corpus Christi Hooks — less hitter-friendly than assumed
    "Nelson Wolff Stadium":             0.785,  # San Antonio Missions — confirmed strong pitcher's park
    "Dickey-Stephens Park":             0.781,  # Arkansas Travelers — confirmed strong pitcher's park


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
