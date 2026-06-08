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
}

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
    if 'in' in t:
        return 'In'
    if 'l-r' in t or 'r-l' in t or 'left' in t or 'right' in t:
        return 'Cross'
    if 'calm' in t or t.strip() == '':
        return 'Calm'
    return 'Cross'


# ---------------------------------------------------------------------------
# Multiplier calculators
# ---------------------------------------------------------------------------
def _temp_multiplier(temp_f: float) -> float:
    """
    For every 10°F above 70°F: +3.5%
    For every 10°F below 65°F: -3.5%
    65–70°F: neutral
    Hard clamped to ±15%.
    """
    if temp_f > 70:
        adj = ((temp_f - 70) / 10) * 0.035
    elif temp_f < 65:
        adj = -((65 - temp_f) / 10) * 0.035
    else:
        adj = 0.0
    return round(1.0 + max(-0.15, min(0.15, adj)), 4)


def _wind_multiplier(wind_mph: float, wind_dir: str) -> float:
    """
    Out tailwind  > 10 MPH : 1.08–1.15 (scales linearly up to 25 MPH)
    Out tailwind  5–10 MPH : 1.03–1.07
    In headwind   > 10 MPH : 0.88–0.93
    In headwind   5–10 MPH : 0.93–0.97
    Crosswind               : 0.99–1.01 (minor)
    Calm (< 5 MPH)          : 1.00
    """
    if wind_dir in ('Indoor', 'Calm') or wind_mph < 5:
        return 1.0

    if wind_dir == 'Out':
        if wind_mph <= 10:
            # Linear: 5→1.03, 10→1.07
            adj = 0.03 + ((wind_mph - 5) / 5) * 0.04
        else:
            # Linear: 10→1.08, 25+→1.15 (capped)
            adj = 0.08 + min((wind_mph - 10) / 15, 1.0) * 0.07
        return round(1.0 + adj, 4)

    if wind_dir == 'In':
        if wind_mph <= 10:
            # Linear: 5→-0.03, 10→-0.07
            adj = -(0.03 + ((wind_mph - 5) / 5) * 0.04)
        else:
            # Linear: 10→-0.08, 25+→-0.12 (capped)
            adj = -(0.08 + min((wind_mph - 10) / 15, 1.0) * 0.04)
        return round(1.0 + adj, 4)

    if wind_dir == 'Cross':
        # Very minor impact; slight negative as crosswinds affect trajectory
        adj = -min(wind_mph * 0.001, 0.01)
        return round(1.0 + adj, 4)

    return 1.0


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
            temp    = int(m.group(1))
            wind_mph = int(m.group(2))
            wind_dir = _parse_wind_dir(m.group(3))
        else:
            # Temp only (calm)
            t = _TEMP_ONLY_RE.search(txt)
            temp     = int(t.group(1)) if t else 72
            wind_mph = 0
            wind_dir = 'Calm'

        result[key] = {
            'temp': temp, 'wind_mph': wind_mph,
            'wind_dir': wind_dir, 'rain_pct': rain_pct, 'is_dome': False
        }

    return result


# ---------------------------------------------------------------------------
# wttr.in fallback
# ---------------------------------------------------------------------------
def _get_wttr_weather(venue_name: str) -> dict:
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
        current = data['current_condition'][0]
        temp_f   = round((int(current['temp_C']) * 9/5) + 32)
        wind_mph = int(current['windspeedMiles'])
        wind_deg = int(current['winddirDegree'])
        # Map compass degrees to simplified In/Out/Cross using stadium orientation
        # MLB stadiums face roughly ENE (bearing ~60-70°). Wind from S/SW blows 'Out',
        # from N/NE blows 'In'. We use a simplified 4-quadrant mapping.
        if 45 <= wind_deg <= 225:   # wind from E/S/W sector → generally blows toward OF
            wind_dir = 'Out'
        elif wind_deg > 225 or wind_deg < 45:   # wind from N sector → blows toward HP
            wind_dir = 'In'
        else:
            wind_dir = 'Cross'
        return {'temp': temp_f, 'wind_mph': wind_mph,
                'wind_dir': wind_dir, 'rain_pct': 0, 'is_dome': False}
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
def get_weather_modifier(venue_name: str, away_abbr: str = None, home_abbr: str = None) -> dict:
    """
    Returns a weather context dict for a given venue.

    Parameters
    ----------
    venue_name : str   e.g. "Wrigley Field"
    away_abbr  : str   2-3 letter team abbreviation from RotoWire (e.g. "CHC")
    home_abbr  : str

    Returns dict with keys:
        temp, wind_mph, wind_dir, is_indoor,
        temp_multiplier, wind_multiplier, weather_multiplier, weather_label
    """
    _load_rotowire_cache()

    # --- Step 1: Determine roof type ---
    roof_type = get_roof_type(venue_name)

    # --- Step 2: Fetch raw weather ---
    raw = None

    # Try RotoWire cache first using team abbrs
    if away_abbr and home_abbr and _rotowire_cache:
        key = f"{away_abbr}@{home_abbr}"
        raw = _rotowire_cache.get(key)

    # If no abbrs or not found in cache, try matching by partial key
    if raw is None and _rotowire_cache:
        # Try to find any key that references either abbreviation
        if away_abbr or home_abbr:
            for k, v in _rotowire_cache.items():
                parts = k.split('@')
                if len(parts) == 2:
                    if (away_abbr and away_abbr in parts[0]) or \
                       (home_abbr and home_abbr in parts[1]):
                        raw = v
                        break

    # Fallback: wttr.in
    if raw is None:
        raw = _get_wttr_weather(venue_name)

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

    # --- Step 4: Calculate multipliers ---
    if is_indoor:
        temp_f   = INDOOR_TEMP
        wind_mph = INDOOR_WIND
        wind_dir = 'Indoor'
        t_mult   = 1.0
        w_mult   = 1.0
    else:
        temp_f   = raw.get('temp', 72)
        wind_mph = raw.get('wind_mph', 0)
        wind_dir = raw.get('wind_dir', 'Calm')
        t_mult   = _temp_multiplier(temp_f)
        w_mult   = _wind_multiplier(wind_mph, wind_dir)

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
        'is_indoor':          is_indoor,
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
    today = datetime.datetime.now().strftime('%m/%d/%Y')
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
