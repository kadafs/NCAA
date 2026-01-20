import os
import requests
import xml.etree.ElementTree as ET
import json
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
DATA_DIR = os.path.join(ROOT_DIR, "data")
MATCHUPS_FILE = os.path.join(DATA_DIR, "eurocup_matchups.json")

def fetch_eurocup_schedule(target_date=None):
    if target_date is None:
        target_date = get_target_date()
        
    date_str = target_date.strftime("%Y-%m-%d")
    print(f"Fetching EuroCup schedule for {date_str}...")
    
    # Competition code 'U' for EuroCup, Season 'U2025'
    url = "https://api-live.euroleague.net/v1/schedules?seasonCode=U2025"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/xml"
    }
    
    # XML format is "Jan 20, 2026"
    today_val = target_date.strftime("%b %d, %Y")
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        
        matchups = []
        
        # The XML structure has items under schedule
        for game in root.findall(".//item"):
            game_date = game.find('date').text # Format: "Jan 20, 2026"
            
            if game_date == today_val:
                away_name = game.find('awayteam').text
                home_name = game.find('hometeam').text
                
                matchups.append({
                    "away": away_name,
                    "home": home_name,
                    "away_city": away_name.split(" ")[0],
                    "home_city": home_name.split(" ")[0],
                    "game_time": game.find('startime').text if game.find('startime') is not None else "TBD",
                    "total": 165.0, # Placeholder
                })

        if not os.path.exists(DATA_DIR):
            os.makedirs(DATA_DIR)
            
        with open(MATCHUPS_FILE, "w", encoding="utf-8") as f:
            json.dump(matchups, f, indent=2)
            
        print(f"Found {len(matchups)} EuroCup games for {today_val}.")
        return matchups

    except Exception as e:
        print(f"Error fetching EuroCup schedule: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_eurocup_schedule(target)
