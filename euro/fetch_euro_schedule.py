import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import zoneinfo

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "euro_matchups.json")

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def fetch_euro_daily_schedule():
    print("Fetching EuroLeague schedule (XML v1/results)...")
    
    # Use ET for consistency across the dashboard
    now = datetime.now(ET_TZ)
    today_str = now.strftime("%d/%m/%Y") # EuroLeague format in XML results
    
    # EuroLeague results endpoint provides the season's games
    url = "https://api-live.euroleague.net/v1/results?seasonCode=E2024"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse XML
        root = ET.fromstring(response.content)
        
        # Structure looks like <results><game><gamecode>...
        all_games = root.findall('game')
        print(f"Total games in season XML: {len(all_games)}")
        
        matchups = []
        for g in all_games:
            gdate = g.find('date').text if g.find('date') is not None else ""
            
            # Match today's date
            if today_str in gdate:
                away_el = g.find('away')
                home_el = g.find('home')
                
                away_name = away_el.text if away_el is not None else "Unknown"
                home_name = home_el.text if home_el is not None else "Unknown"
                
                matchups.append({
                    "away": away_name,
                    "home": home_name,
                    "away_city": away_name.split(" ")[0],
                    "home_city": home_name.split(" ")[0],
                    "game_time": "TBD", # XML results usually don't have time for future games
                    "game_code": g.find('gamecode').text if g.find('gamecode') is not None else ""
                })
        
        print(f"Found {len(matchups)} EuroLeague games for {today_str}.")
        
        with open(MATCHUP_FILE, "w", encoding="utf-8") as f:
            json.dump(matchups, f, indent=2)
            
        return matchups

    except Exception as e:
        print(f"Error fetching EuroLeague schedule: {e}")
        # If XML fails, try the Header fallback for today?
        return []

if __name__ == "__main__":
    fetch_euro_daily_schedule()
