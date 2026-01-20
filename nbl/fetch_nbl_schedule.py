import requests
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mapping import get_target_date

def fetch_nbl_schedule(target_date=None):
    """
    Fetches the NBL schedule from the Rosetta API.
    """
    if target_date is None:
        target_date = get_target_date()
    
    # NBL API for all matches in 2024-26 season (ID 2025 is used for 2024-25 and 2025-26)
    url = "https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/2025/all"
    headers = {
        "Origin": "https://nbl.com.au",
        "Referer": "https://nbl.com.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Fetching NBL schedule for {target_date.strftime('%Y-%m-%d')}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        matches = data.get("data", [])
        daily_matchups = []
        
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        for match in matches:
            # Match date format: "2024-09-19T09:30:00"
            match_start = match.get("start_time", "")
            if not match_start:
                continue
                
            match_date_str = match_start.split("T")[0]
            
            if match_date_str == target_date_str:
                home_team = match.get("home_team", {})
                away_team = match.get("away_team", {})
                
                matchup = {
                    "game_id": match.get("id"),
                    "home_team": home_team.get("name"),
                    "away_team": away_team.get("name"),
                    "home_tricode": home_team.get("tricode"),
                    "away_tricode": away_team.get("tricode"),
                    "start_time": match_start,
                    "status": match.get("match_status")
                }
                daily_matchups.append(matchup)
        
        print(f"Found {len(daily_matchups)} NBL games for {target_date_str}.")
        
        # Save to data directory
        os.makedirs("data", exist_ok=True)
        with open("data/nbl_matchups.json", "w") as f:
            json.dump(daily_matchups, f, indent=4)
            
        return daily_matchups
        
    except Exception as e:
        print(f"Error fetching NBL schedule: {e}")
        return []

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_nbl_schedule(target)
