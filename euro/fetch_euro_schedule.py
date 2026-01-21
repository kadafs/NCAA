import os
import json
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import zoneinfo
import argparse
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import get_target_date

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "euro_matchups.json")

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def fetch_euro_daily_schedule(target_date=None):
    if target_date is None:
        target_date = get_target_date()
        
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"Fetching EuroLeague hybrid schedule/results for {date_str}...")
    
    # Format matches XML: "Oct 17, 2025" or "Jan 21, 2026"
    today_str = target_date.strftime("%b %d, %Y")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml"
    }
    
    try:
        # 1. Fetch Full Season Schedule (The Source of Truth for "When/Who")
        sched_url = "https://api-live.euroleague.net/v1/schedules?seasonCode=E2025"
        sched_resp = requests.get(sched_url, headers=headers)
        sched_resp.raise_for_status()
        sched_root = ET.fromstring(sched_resp.content)
        
        # 2. Fetch Results (The Source of Truth for "Scores/Played")
        res_url = "https://api-live.euroleague.net/v1/results?seasonCode=E2025"
        res_resp = requests.get(res_url, headers=headers)
        res_resp.raise_for_status()
        res_root = ET.fromstring(res_resp.content)
        
        # Map results by game_code for easy overlay
        results_map = {}
        for g in res_root.findall('game'):
            gc = g.find('gamecode').text if g.find('gamecode') is not None else ""
            if gc:
                results_map[gc] = {
                    "played": (g.find('played').text.lower() == 'true') if g.find('played') is not None else False,
                    "away_score": int(g.find('awayscore').text) if g.find('awayscore') is not None else None,
                    "home_score": int(g.find('homescore').text) if g.find('homescore') is not None else None
                }
        
        # 3. Process Schedule and Overlay Results
        daily_matchups = []
        # v1/schedules uses <item>
        all_games = sched_root.findall('item')
        
        for g in all_games:
            gdate = g.find('date').text if g.find('date') is not None else ""
            
            # Match target date
            if today_str == gdate:
                game_code = g.find('gamecode').text if g.find('gamecode') is not None else ""
                away_name = g.find('awayteam').text if g.find('awayteam') is not None else "Unknown"
                home_name = g.find('hometeam').text if g.find('hometeam') is not None else "Unknown"
                
                # Overlay results if available
                res = results_map.get(game_code, {})
                played = res.get('played', False) or (g.find('played').text.lower() == 'true' if g.find('played') is not None else False)
                
                daily_matchups.append({
                    "away": away_name,
                    "home": home_name,
                    "away_city": away_name.split(" ")[0],
                    "home_city": home_name.split(" ")[0],
                    "game_time": g.find('startime').text if g.find('startime') is not None else "TBD",
                    "game_code": game_code,
                    "played": played,
                    "away_score": res.get('away_score'),
                    "home_score": res.get('home_score'),
                    "total": 165.5 
                })
        
        print(f"Found {len(daily_matchups)} EuroLeague games for {today_str}.")
        
        with open(MATCHUP_FILE, "w", encoding="utf-8") as f:
            json.dump(daily_matchups, f, indent=2)
            
        return daily_matchups

    except Exception as e:
        print(f"Error fetching EuroLeague schedule: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_euro_daily_schedule(target)
