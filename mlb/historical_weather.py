import statsapi
import re
from weather_f5 import _temp_multiplier, _wind_multiplier, _temp_fatigue_scaler

def get_historical_weather(game_id):
    """
    Fetches the historical weather recorded at game time from the MLB Stats API boxscore.
    Returns the same context dictionary format as weather_f5.get_weather_modifier.
    """
    try:
        box = statsapi.boxscore_data(game_id)
        info = box.get('gameBoxInfo', [])
    except Exception as e:
        print(f"Error fetching historical weather for {game_id}: {e}")
        return None
        
    weather_str = ""
    wind_str = ""
    for item in info:
        if item.get('label') == 'Weather':
            weather_str = item.get('value', '')
        elif item.get('label') == 'Wind':
            wind_str = item.get('value', '')
            
    # Default fallback
    temp = 72
    m = re.search(r'(\d+)\s*degrees', weather_str, re.IGNORECASE)
    if m: temp = int(m.group(1))
    
    wind_mph = 0
    m = re.search(r'(\d+)\s*mph', wind_str, re.IGNORECASE)
    if m: wind_mph = int(m.group(1))
    
    # Roof logic
    is_indoor = False
    if 'dome' in weather_str.lower() or 'indoor' in weather_str.lower() or 'roof closed' in weather_str.lower():
        is_indoor = True
        
    wind_dir = 'Calm'
    wind_lateral = None
    if not is_indoor:
        lower_wind = wind_str.lower()
        if 'out' in lower_wind: wind_dir = 'Out'
        elif 'in ' in lower_wind or lower_wind.endswith(' in.'): wind_dir = 'In'
        elif 'l to r' in lower_wind or 'left to right' in lower_wind or 'l-r' in lower_wind:
            wind_dir = 'Cross'
            wind_lateral = 'L-R'
        elif 'r to l' in lower_wind or 'right to left' in lower_wind or 'r-l' in lower_wind:
            wind_dir = 'Cross'
            wind_lateral = 'R-L'
        elif 'calm' in lower_wind: wind_dir = 'Calm'
        elif wind_mph > 0: wind_dir = 'Cross'
        
    if is_indoor:
        temp = 72
        wind_mph = 0
        wind_dir = 'Indoor'
        wind_lateral = None
        t_mult = 1.0
        w_mult = 1.0
        fatigue = 1.0
    else:
        t_mult = _temp_multiplier(temp)
        w_mult = _wind_multiplier(wind_mph, wind_dir)
        fatigue = _temp_fatigue_scaler(temp)
        
    combined = round(1.0 + (t_mult - 1.0) + (w_mult - 1.0), 4)
    
    pct_change = round((combined - 1.0) * 100, 1)
    sign = '+' if pct_change >= 0 else ''
    wind_label = f"{wind_mph} MPH {wind_dir}" if wind_mph >= 5 else "Calm"
    if is_indoor:
        label = "Indoor / Roof Closed (Historical)"
    else:
        label = f"{temp}F | {wind_label} | Weather: {sign}{pct_change}% (Historical)"
        
    return {
        'temp': temp,
        'wind_mph': wind_mph,
        'wind_dir': wind_dir,
        'wind_lateral': wind_lateral,
        'is_indoor': is_indoor,
        'temp_fatigue_scaler': fatigue,
        'temp_multiplier': t_mult,
        'wind_multiplier': w_mult,
        'weather_multiplier': combined,
        'weather_label': label
    }

if __name__ == '__main__':
    # Test a few games
    print(get_historical_weather(745672)) # Oakland Coliseum
