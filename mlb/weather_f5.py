from mlb_time import get_mlb_now
"""
weather_f5.py
=============
Fetches and parses game-day weather from RotoWire's MLB Lineups page.
Applies a three-stage roof/dome filter, then computes a combined
weather multiplier (temperature + wind) for F5 run projections.

Primary source: RotoWire (https://www.rotowire.com/baseball/daily-lineups.php)
Fallback:       wttr.in JSON API + static stadium coordinates

Output per game:
    {
        'temp':               82,
        'wind_mph':           14,
        'wind_dir':           'Out',
        'is_indoor':          False,
        'temp_multiplier':    1.042,
        'wind_multiplier':    1.10,
        'weather_multiplier': 1.145,   # combined, already rounded to 4dp
        'weather_label':      '82F | 14 MPH Out | Weather: +14.5%'
    }
"""

import re
import time
import requests
from bs4 import BeautifulSoup

from stadium_config import get_roof_type, INDOOR_TEMP, INDOOR_WIND

# ---------------------------------------------------------------------------
# Stadium lat/lng for wttr.in fallback
# ---------------------------------------------------------------------------
STADIUM_COORDS = {
    "Truist Park":                    (33.8908, -84.4678),
    "Citizens Bank Park":             (39.9056, -75.1665),
    "Yankee Stadium":                 (40.8296, -73.9262),
    "Rogers Centre":                  (43.6414, -79.3894),
    "Comerica Park":                  (42.3390, -83.0485),
    "loanDepot park":                 (25.7781, -80.2197),
    "Daikin Park":                    (29.7572, -95.3555),
    "Target Field":                   (44.9817, -93.2783),
    "Busch Stadium":                  (38.6226, -90.1928),
    "Globe Life Field":               (32.7473, -97.0845),
    "Coors Field":                    (39.7559, -104.9942),
    "Chase Field":                    (33.4453, -112.0667),
    "UNIQLO Field at Dodger Stadium": (34.0739, -118.2400),
    "Dodger Stadium":                 (34.0739, -118.2400),
    "Petco Park":                     (32.7073, -117.1566),
    "Wrigley Field":                  (41.9484, -87.6553),
    "Oracle Park":                    (37.7786, -122.3893),
    "T-Mobile Park":                  (47.5914, -122.3325),
    "Kauffman Stadium":               (39.0517, -94.4803),
    "Great American Ball Park":       (39.0979, -84.5082),
    "Fenway Park":                    (42.3467, -71.0972),
    "PNC Park":                       (40.4469, -80.0057),
    "Progressive Field":              (41.4962, -81.6852),
    "Oriole Park at Camden Yards":    (39.2838, -76.6217),
    "Guaranteed Rate Field":          (41.8300, -87.6339),
    "Nationals Park":                 (38.8730, -77.0074),
    "Angel Stadium":                  (33.8003, -117.8827),
    "American Family Field":          (43.0280, -87.9712),
    "Citi Field":                     (40.7571, -73.8458),
    "Tropicana Field":                (27.7683, -82.6534),
    "Las Vegas Ballpark":             (36.1716, -115.1461),
    "Sutter Health Park":             (38.5840, -121.5001),  # Sacramento

    # ── AAA — Pacific Coast League (PCL) ─────────────────────────────────────
    "Greater Nevada Field":           (39.5296, -119.7820),  # Reno (~4,400ft)
    "Isotopes Park":                  (35.0956, -106.6500),  # Albuquerque (~5,300ft)
    "Constellation Field":            (29.6111, -95.5583),  # Sugar Land TX
    "Chickasaw Bricktown Ballpark":   (35.4676, -97.5164),  # Oklahoma City
    "Principal Park":                 (41.5724, -93.6240),  # Des Moines IA
    "Momentum Bank Ballpark":         (31.9968, -102.0779), # Midland TX
    "Toyota Field":                   (34.7304, -86.5861),  # Madison AL (Rocket City)
    "Round Rock":                     (30.5114, -97.6792),  # Dell Diamond, Round Rock TX

    # ── AAA — International League (IL) ──────────────────────────────────────
    "Truist Field":                   (35.2271, -80.8431),  # Charlotte NC
    "Louisville Slugger Field":       (38.2570, -85.7438),  # Louisville KY
    "Victory Field":                  (39.7782, -86.1625),  # Indianapolis IN
    "Harbor Park":                    (36.8463, -76.3003),  # Norfolk VA
    "Polar Park":                     (42.2636, -71.8022),  # Worcester MA
    "Gwinnett Field":                 (33.8487, -84.0672),  # Lawrenceville GA
    "Sahlen Field":                   (42.8866, -78.8765),  # Buffalo NY
    "Coca-Cola Park":                 (40.6131, -75.4706),  # Lehigh Valley PA
    "VyStar Ballpark":                (30.3232, -81.6557),  # Jacksonville FL
    "Vystar Ballpark":                (30.3232, -81.6557),  # Jacksonville FL (alias)
    "Durham Bulls Athletic Park":     (35.9796, -78.8913),  # Durham NC
    "AutoZone Park":                  (35.1495, -90.0490),  # Memphis TN
    "Dunkin' Park":                   (41.7659, -72.6733),  # Hartford CT

    # ── AA — Eastern League (EL) ─────────────────────────────────────────────
    "Delta Dental Stadium":           (43.6615, -70.2797),  # Portland ME
    "TD Bank Ballpark":               (40.5709, -74.6138),  # Bridgewater NJ (Somerset)
    "UPMC Park":                      (42.1292, -80.0859),  # Erie PA
    "7 17 Credit Union Park":         (41.0748, -81.5187),  # Akron OH
    "Peoples Natural Gas Field":      (40.5061, -78.3994),  # Altoona PA
    "Mirabito Stadium":               (42.1015, -75.9182),  # Binghamton NY
    "FNB Field":                      (40.2732, -76.8867),  # Harrisburg PA
    "FirstEnergy Stadium":            (40.3360, -75.9274),  # Reading PA

    # ── AA — Southern League (SL) ────────────────────────────────────────────
    "Covenant Health Park":           (35.9906, -83.9391),  # Knoxville TN
    "Synovus Park":                   (32.4609, -84.9877),  # Columbus GA
    "Blue Wahoos Stadium":            (30.4243, -87.2169),  # Pensacola FL
    "Riverwalk Stadium":              (32.3668, -86.2999),  # Montgomery AL

    # ── AA — Texas League (TL) ────────────────────────────────────────────────
    "Whataburger Field":              (27.7987, -97.4060),  # Corpus Christi TX
    "ONEOK Field":                    (36.1546, -95.9946),  # Tulsa OK
    "Hodgetown":                      (35.2212, -101.8313), # Amarillo TX
    "Equity Bank Park":               (37.6872, -97.3301),  # Wichita KS
    "Arvest Ballpark":                (36.3823, -94.2083),  # Springdale AR (NWA)
    "Dickey-Stephens Park":           (34.7465, -92.2709),  # North Little Rock AR
    "Nelson Wolff Stadium":           (29.4387, -98.5315),  # San Antonio TX
    "Dr Pepper Ballpark":             (33.1476, -96.8231),  # Frisco TX
    "Hammons Field":                  (37.2044, -93.2985),  # Springfield MO
}


# ---------------------------------------------------------------------------
# Per-stadium center-field bearing (Issue 9 fix)
# ---------------------------------------------------------------------------
# The compass bearing (0°=North, 90°=East) FROM home plate TOWARD center field.
# Wind blowing FROM the OPPOSITE direction blows OUT toward CF.
# Most MLB parks face ENE (~60°) to keep afternoon sun out of the batter's eyes.
# Well-documented exceptions are listed here; unknown parks default to 60°.
#
# Sources: stadium architectural plans, satellite imagery, published research.
STADIUM_CF_BEARING = {
    # ENE-facing (standard, ~60°)
    "Yankee Stadium":                  67,   # faces ESE from HP to CF
    "Citi Field":                      62,
    "Citizens Bank Park":              63,
    "Nationals Park":                  67,
    "Oriole Park at Camden Yards":     60,
    "Progressive Field":               57,
    "PNC Park":                        60,
    "Great American Ball Park":        60,
    "Truist Park":                     65,
    "Busch Stadium":                   63,
    "American Family Field":           60,
    "Globe Life Field":                62,   # retractable, but outdoors when open
    "Kauffman Stadium":                57,
    "Guaranteed Rate Field":           60,
    "Target Field":                    58,
    "Rogers Centre":                   60,   # indoor dome — fallback rarely fires
    "Angel Stadium":                   60,
    "UNIQLO Field at Dodger Stadium":  65,
    "Dodger Stadium":                  65,
    "Petco Park":                      62,
    "Comerica Park":                   58,

    # Notable exceptions
    "Fenway Park":                     34,   # faces NNE; LF is to the SW
    "Wrigley Field":                   21,   # faces NNE; well-known wind tunnel
    "Coors Field":                     69,   # faces ESE into the mountains
    "Oracle Park":                     44,   # faces NE across McCovey Cove
    "T-Mobile Park":                   13,   # faces nearly N; different from most
    "Daikin Park":                     80,   # former Minute Maid; faces E
    "loanDepot park":                  60,   # retractable roof
    "Tropicana Field":                 60,   # indoor
    "Chase Field":                     60,   # retractable roof
}

# Default bearing for parks not in the table
_DEFAULT_CF_BEARING = 60   # ENE — statistically accurate for ~70% of MLB parks


def _wind_relative_to_stadium(wind_deg: int, venue_name: str) -> str:
    """
    Issue 9 fix: converts a compass wind bearing to a stadium-relative direction
    using the per-stadium CF bearing table.

    Logic:
    - wind_blows_toward = (wind_deg + 180) % 360  (wind FROM X blows TOWARD X+180)
    - angular distance from wind_blows_toward to cf_bearing:
        < 50°  → 'Out'   (blowing toward CF)
        < 50° from opposite → 'In'  (blowing toward HP)
        within foul-line cone (±40° of 3B/1B lines) → 'L-R' or 'R-L'
        otherwise → 'Cross' (generic diagonal)
    """
    # Find CF bearing for this venue
    cf_bearing = _DEFAULT_CF_BEARING
    venue_lower = venue_name.lower()
    for name, bearing in STADIUM_CF_BEARING.items():
        if name.lower() in venue_lower or venue_lower in name.lower():
            cf_bearing = bearing
            break

    # Direction the wind is blowing TOWARD
    wind_toward = (wind_deg + 180) % 360

    # Angular distance (0–180°)
    def _ang_dist(a, b):
        d = abs(a - b) % 360
        return d if d <= 180 else 360 - d

    to_cf   = _ang_dist(wind_toward, cf_bearing)
    to_hp   = _ang_dist(wind_toward, (cf_bearing + 180) % 360)
    to_1b   = _ang_dist(wind_toward, (cf_bearing + 90)  % 360)  # 1B side
    to_3b   = _ang_dist(wind_toward, (cf_bearing - 90)  % 360)  # 3B side

    if to_cf <= 50:
        return 'Out'
    if to_hp <= 50:
        return 'In'
    # Foul-line laterals: LHB pulls to RF (1B side), RHB pulls to LF (3B side)
    # Wind toward 1B line = R-L (headwind for LHB pull, tailwind for RHB pull)
    # Wind toward 3B line = L-R
    if to_3b <= 40:
        return 'L-R'
    if to_1b <= 40:
        return 'R-L'
    return 'Cross'

# ---------------------------------------------------------------------------
# Wind direction → relative field impact parser
# ---------------------------------------------------------------------------
# RotoWire uses these terms: 'Out', 'In', 'L-R', 'R-L', 'Calm', 'Dome'
# We normalise anything else to 'Cross'

def _parse_wind_dir(text: str) -> str:
    """Returns one of: 'Out', 'In', 'Cross', 'Calm', 'Indoor'."""
    t = text.lower()
    if 'dome' in t or 'indoor' in t:
        return 'Indoor'
    if 'out' in t:
        return 'Out'
    if 'in' in t and 'wind' not in t:   # 'in' but not 'wind'
        return 'In'
    if 'l-r' in t or 'r-l' in t or 'left' in t or 'right' in t:
        return 'Cross'
    if 'calm' in t or t.strip() == '':
        return 'Calm'
    return 'Cross'


def _parse_wind_lateral(text: str):
    """
    For crosswind games returns 'L-R' or 'R-L'.
    Returns None for Out/In/Calm/Indoor winds.
    L-R = blowing from LF toward RF (left-to-right from batter's perspective).
    R-L = blowing from RF toward LF.
    """
    t = text.lower()
    if 'l-r' in t or 'left to right' in t or 'left-to-right' in t:
        return 'L-R'
    if 'r-l' in t or 'right to left' in t or 'right-to-left' in t:
        return 'R-L'
    return None


# ---------------------------------------------------------------------------
# Multiplier calculators
# ---------------------------------------------------------------------------
def _temp_multiplier(temp_f: float) -> float:
    """
    For every 10°F above 70°F: +1.5% (Dampened from 3.5%)
    For every 10°F below 65°F: -1.5%
    65–70°F: neutral
    Hard clamped to ±10%.
    """
    if temp_f > 70:
        adj = ((temp_f - 70) / 10) * 0.015
    elif temp_f < 65:
        adj = -((65 - temp_f) / 10) * 0.015
    else:
        adj = 0.0
    return round(1.0 + max(-0.10, min(0.10, adj)), 4)


def _wind_multiplier(wind_mph: float, wind_dir: str) -> float:
    """
    Out tailwind  > 10 MPH : 1.03–1.07 (scales linearly up to 25 MPH)
    Out tailwind  5–10 MPH : 1.01–1.03
    In headwind   > 10 MPH : 0.93–0.97
    In headwind   5–10 MPH : 0.97–0.99
    Crosswind               : 1.00 (minor)
    Calm (< 5 MPH)          : 1.00
    """
    if wind_dir in ('Indoor', 'Calm') or wind_mph < 5:
        return 1.0

    if wind_dir == 'Out':
        if wind_mph <= 10:
            # Linear: 5→1.01, 10→1.03
            adj = 0.01 + ((wind_mph - 5) / 5) * 0.02
        else:
            # Linear: 10→1.03, 25+→1.07 (capped)
            adj = 0.03 + min((wind_mph - 10) / 15, 1.0) * 0.04
        return round(1.0 + adj, 4)

    if wind_dir == 'In':
        if wind_mph <= 10:
            # Linear: 5→-0.01, 10→-0.03
            adj = -(0.01 + ((wind_mph - 5) / 5) * 0.02)
        else:
            # Linear: 10→-0.03, 25+→-0.07 (capped)
            adj = -(0.03 + min((wind_mph - 10) / 15, 1.0) * 0.04)
        return round(1.0 + adj, 4)

    if wind_dir == 'Cross':
        # Very minor impact; handled separately via handedness in MC engine
        return 1.0

    return 1.0


def _temp_fatigue_scaler(temp_f: float) -> float:
    """
    Returns a TTTO fatigue acceleration multiplier based on temperature.
    Hot weather (>85°F): pitcher degrades faster through the order (+up to 15%)
    Cool weather (<65°F): pitcher degrades slower (-up to 8%)
    """
    if temp_f > 85:
        return round(1.0 + ((temp_f - 85) / 15) * 0.15, 4)  # +15% at 100°F
    elif temp_f < 65:
        return round(1.0 - ((65 - temp_f) / 20) * 0.08, 4)  # -8% at 45°F
    return 1.0


def get_thermal_adjusted_ip(base_projected_ip: float, temp_f: float) -> float:
    """
    Predictive Volatility Fix: Dynamically shortens a starting pitcher's 
    projected innings under extreme heat conditions to mirror manager hooks.
    """
    if temp_f > 92:
        # Programmatically reduce length by 8% due to rapid dehydration fatigue
        return round(max(2.0, base_projected_ip * 0.92), 2)
    elif temp_f > 85:
        return round(max(2.0, base_projected_ip * 0.96), 2)
    return base_projected_ip


# ---------------------------------------------------------------------------
# RotoWire scraper
# ---------------------------------------------------------------------------
ROTOWIRE_URL = "https://www.rotowire.com/baseball/daily-lineups.php"
ROTOWIRE_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

# Regex to extract temp and wind from RotoWire's bottom bar text
# Matches patterns like: "81° Wind 11 mph Out" or "87° Wind 15 mph L-R" or "Dome In Domed Stadium"
_WEATHER_RE = re.compile(
    r'(\d{2,3})[°\u00b0]?\s*Wind\s+(\d+)\s*mph\s+([A-Za-z\-]+)',
    re.IGNORECASE
)
_DOME_RE = re.compile(r'dome|domed', re.IGNORECASE)
_TEMP_ONLY_RE = re.compile(r'(\d{2,3})[°\u00b0]')
_RAIN_RE = re.compile(r'(\d+)%')   # Rain chance percentage (appears before temp on RotoWire)


def _scrape_rotowire() -> dict:
    """
    Returns {team_abbr_pair: {'temp':int,'wind_mph':int,'wind_dir':str,'rain_pct':int}}
    Key is 'AWAY@HOME' using 2-3 letter abbreviations.
    Raises on failure so caller can try fallback.
    """
    r = requests.get(ROTOWIRE_URL, headers=ROTOWIRE_HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    result = {}

    for box in soup.find_all('div', class_='lineup__box'):
        abbrs = box.find_all('div', class_='lineup__abbr')
        if len(abbrs) < 2:
            continue
        away_abbr = abbrs[0].get_text(strip=True)
        home_abbr = abbrs[1].get_text(strip=True)
        key = f"{away_abbr}@{home_abbr}"

        bottom = box.find('div', class_='lineup__bottom')
        if not bottom:
            continue
        txt = bottom.get_text(separator=' ', strip=True)

        # Check for dome/indoor first
        if _DOME_RE.search(txt):
            result[key] = {'temp': INDOOR_TEMP, 'wind_mph': INDOOR_WIND,
                           'wind_dir': 'Indoor', 'rain_pct': 0, 'is_dome': True}
            continue

        # Extract rain chance (first % number)
        rain_match = _RAIN_RE.search(txt)
        rain_pct = int(rain_match.group(1)) if rain_match else 0

        # Extract temp + wind
        m = _WEATHER_RE.search(txt)
        if m:
            temp     = int(m.group(1))
            wind_mph = int(m.group(2))
            wind_dir = _parse_wind_dir(m.group(3))
            wind_lateral = _parse_wind_lateral(m.group(3))
        else:
            # Temp only (calm)
            t = _TEMP_ONLY_RE.search(txt)
            wind_dir = 'Calm'
            wind_lateral = None

        result[key] = {
            'temp': temp, 'wind_mph': wind_mph,
            'wind_dir': wind_dir, 'wind_lateral': wind_lateral,
            'rain_pct': rain_pct, 'is_dome': False
        }

    return result


# ---------------------------------------------------------------------------
# wttr.in fallback
# ---------------------------------------------------------------------------
def _get_wttr_weather(venue_name: str, target_date: str = None) -> dict:
    """Fetches raw temp + wind for a stadium via wttr.in JSON."""
    # Find closest match in coords table
    coords = None
    venue_lower = venue_name.lower()
    for name, c in STADIUM_COORDS.items():
        if name.lower() in venue_lower or venue_lower in name.lower():
            coords = c
            break

    if not coords:
        return None

    lat, lng = coords
    url = f"https://wttr.in/{lat},{lng}?format=j1"
    try:
        r = requests.get(url, timeout=8)
        data = r.json()
        
        target_weather = None
        if target_date and 'weather' in data:
            for day in data['weather']:
                if day.get('date') == target_date:
                    hourlies = day.get('hourly', [])
                    for h in hourlies:
                        # Grab 1800 (6 PM) forecast, or 1500 (3 PM) as fallback
                        if h.get('time') in ('1500', '1800'):
                            target_weather = h
                            if h.get('time') == '1800':
                                break
                    if not target_weather and hourlies:
                        target_weather = hourlies[0]
                    break

        if target_weather:
            temp_f   = round((int(target_weather['tempC']) * 9/5) + 32)
            wind_mph = int(target_weather['windspeedMiles'])
            wind_deg = int(target_weather['winddirDegree'])
        else:
            current = data['current_condition'][0]
            temp_f   = round((int(current['temp_C']) * 9/5) + 32)
            wind_mph = int(current['windspeedMiles'])
            wind_deg = int(current['winddirDegree'])

        # Map compass degrees to stadium-relative direction
        # Issue 9 fix: uses per-stadium CF bearing instead of a single global quadrant.
        wind_dir   = _wind_relative_to_stadium(wind_deg, venue_name)
        wind_lateral = wind_dir if wind_dir in ('L-R', 'R-L') else None
        # Normalise Cross back to the simplified token the rest of the system expects
        if wind_dir == 'Cross':
            wind_dir = 'Cross'
        return {'temp': temp_f, 'wind_mph': wind_mph,
                'wind_dir': wind_dir, 'wind_lateral': None,
                'rain_pct': 0, 'is_dome': False}
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Module-level cache (populated once per run)
# ---------------------------------------------------------------------------
_rotowire_cache = None
_cache_loaded = False

def _load_rotowire_cache():
    global _rotowire_cache, _cache_loaded
    if _cache_loaded:
        return
    try:
        _rotowire_cache = _scrape_rotowire()
        print(f"[Weather] RotoWire loaded: {len(_rotowire_cache)} games")
    except Exception as e:
        print(f"[Weather] RotoWire scrape failed ({e}), will use wttr.in fallback per game")
        _rotowire_cache = {}
    _cache_loaded = True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_weather_modifier(venue_name: str, away_abbr: str = None, home_abbr: str = None, target_date: str = None) -> dict:
    """
    Returns a weather context dict for a given venue.

    Parameters
    ----------
    venue_name : str   e.g. "Wrigley Field"
    away_abbr  : str   2-3 letter team abbreviation from RotoWire (e.g. "CHC")
    home_abbr  : str
    target_date: str   e.g. "2026-07-04"

    Returns dict with keys:
        temp, wind_mph, wind_dir, is_indoor,
        temp_multiplier, wind_multiplier, weather_multiplier, weather_label
    """
    _load_rotowire_cache()

    # --- Step 1: Determine roof type ---
    roof_type = get_roof_type(venue_name)

    # --- Step 2: Fetch raw weather ---
    raw = None

    # Clean abbreviation dictionary lookup map
    ROTO_MAP = {'WAS': 'WSH', 'SDG': 'SD', 'SFO': 'SF', 'TAMP': 'TB', 'KC': 'KCR'}
    
    clean_away = ROTO_MAP.get(away_abbr, away_abbr) if away_abbr else None
    clean_home = ROTO_MAP.get(home_abbr, home_abbr) if home_abbr else None
    
    today_str = get_mlb_now().strftime('%Y-%m-%d')
    # RotoWire only works for today
    if clean_away and clean_home and _rotowire_cache and (not target_date or target_date == today_str):
        key = f"{clean_away}@{clean_home}"
        raw = _rotowire_cache.get(key)

    # Fallback: wttr.in (supports multi-day forecast if target_date is provided)
    if raw is None:
        raw = _get_wttr_weather(venue_name, target_date)

    # If all else fails, use neutral defaults
    if raw is None:
        raw = {'temp': 72, 'wind_mph': 0, 'wind_dir': 'Calm', 'rain_pct': 0, 'is_dome': False}

    # --- Step 3: Apply roof logic ---
    is_indoor = False

    if roof_type == 'dome' or raw.get('is_dome'):
        is_indoor = True
    elif roof_type == 'retractable':
        rain_pct = raw.get('rain_pct', 0)
        temp     = raw.get('temp', 72)
        # Roof likely closed if: rain > 50%, very cold (<55°F), or very hot (>95°F)
        if rain_pct > 50 or temp < 55 or temp > 95:
            is_indoor = True

    # --- Step 4: Calculate multipliers and physical deltas ---
    if is_indoor:
        temp_f       = INDOOR_TEMP
        wind_mph     = INDOOR_WIND
        wind_dir     = 'Indoor'
        wind_lateral = None
        t_mult   = 1.0
        w_mult   = 1.0
        t_hr_d   = 0.0
        t_pwr_d  = 0.0
        w_hr_d   = 0.0
        w_pwr_d  = 0.0
        fatigue_scaler = 1.0
    else:
        temp_f       = raw.get('temp', 72)
        wind_mph     = raw.get('wind_mph', 0)
        wind_dir     = raw.get('wind_dir', 'Calm')
        wind_lateral = raw.get('wind_lateral', None)
        # Legacy combined multipliers (kept for Top-Down model)
        t_mult   = _temp_multiplier(temp_f)
        w_mult   = _wind_multiplier(wind_mph, wind_dir)
        fatigue_scaler = _temp_fatigue_scaler(temp_f)

    # Revert to compounding multiplication to prevent model calculation drift
    combined = round(t_mult * w_mult, 4)

    # Build human-readable label
    if is_indoor:
        label = "Indoor / Roof Closed | No weather adjustment"
    else:
        pct_change = round((combined - 1.0) * 100, 1)
        sign = '+' if pct_change >= 0 else ''
        wind_str = f"{wind_mph} MPH {wind_dir}" if wind_mph >= 5 else "Calm"
        label = f"{temp_f}F | {wind_str} | Weather: {sign}{pct_change}%"

    return {
        'temp':               temp_f,
        'wind_mph':           wind_mph,
        'wind_dir':           wind_dir,
        'wind_lateral':       wind_lateral if not is_indoor else None,
        'is_indoor':          is_indoor,
        'rain_pct':           raw.get('rain_pct', 0),
        # Fatigue scaler for TTTO acceleration (Fix 4)
        'temp_fatigue_scaler': fatigue_scaler,
        # Legacy combined multiplier (kept for Top-Down model in grade_f5)
        'temp_multiplier':    t_mult,
        'wind_multiplier':    w_mult,
        'weather_multiplier': combined,
        'weather_label':      label,
    }


# ---------------------------------------------------------------------------
# Standalone test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import statsapi, datetime
    today = get_mlb_now().strftime('%m/%d/%Y')
    schedule = statsapi.schedule(sportId=1, date=today)

    print(f"\n{'='*60}")
    print(f"  WEATHER PREVIEW — {today}")
    print(f"{'='*60}\n")

    for game in schedule:
        venue = game.get('venue_name', 'Unknown')
        away  = game['away_name']
        home  = game['home_name']
        ctx   = get_weather_modifier(venue)
        mult_pct = round((ctx['weather_multiplier'] - 1.0) * 100, 1)
        sign = '+' if mult_pct >= 0 else ''
        print(f"  {away} @ {home}")
        print(f"  Venue: {venue}  |  {ctx['weather_label']}")
        print(f"  Combined Multiplier: {ctx['weather_multiplier']}x ({sign}{mult_pct}%)")
        print()
