import requests
import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.mapping import get_target_date

def fetch_acb_schedule(target_date=None, round_id=5899):
    """
    Fetches the ACB schedule (matches) for a specific round or date.
    Note: Reconstructed from standings endpoint to avoid 401 on schedule endpoint.
    """
    if target_date is None:
        target_date = get_target_date()
        
    url = f"https://api2.acb.com/api/seasondata/Competition/standings?competitionId=1&editionId=90&roundId={round_id}"
    
    headers = {
        "Origin": "https://acb.com",
        "Referer": "https://acb.com/",
        "Accept": "application/json",
        "x-apikey": "0dd94928-6f57-4c08-a3bd-b1b2f092976e",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Fetching ACB schedule (via standings) for Round {round_id}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        standing_entries = data.get("standings", [])
        teams_ref = data.get("teams", [])
        
        # Mapping for team names/tricodes
        id_to_name = {t.get("id"): t.get("fullName") for t in teams_ref}
        id_to_tri = {t.get("id"): t.get("abbreviatedName") for t in teams_ref}
        
        seen_matches = set()
        daily_matchups = []
        target_date_str = target_date.strftime("%Y-%m-%d")
        
        for entry in standing_entries:
            rounds = entry.get("rounds", [])
            for r in rounds:
                match = r.get("matchData")
                if not match: continue
                
                m_id = match.get("id")
                if m_id in seen_matches: continue
                
                match_start = match.get("startDateTime", "")
                if not match_start: continue
                
                if match_start.split("T")[0] == target_date_str:
                    home_id = match.get("homeTeamId")
                    away_id = match.get("awayTeamId")
                    
                    matchup = {
                        "game_id": m_id,
                        "home_team": id_to_name.get(home_id),
                        "away_team": id_to_name.get(away_id),
                        "home_tricode": id_to_tri.get(home_id),
                        "away_tricode": id_to_tri.get(away_id),
                        "start_time": match_start,
                        "status": match.get("matchStatus")
                    }
                    daily_matchups.append(matchup)
                    seen_matches.add(m_id)
        
        print(f"Found {len(daily_matchups)} ACB games for {target_date_str} in Round {round_id}.")
        
        # Save to data directory
        os.makedirs("data", exist_ok=True)
        with open("data/acb_matchups.json", "w") as f:
            json.dump(daily_matchups, f, indent=4)
            
        return daily_matchups
        
    except Exception as e:
        print(f"Error fetching ACB schedule: {e}")
        return []

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Target date (YYYY-MM-DD)")
    parser.add_argument("--round", type=int, default=5899, help="ACB Round ID")
    args = parser.parse_args()
    
    target = get_target_date(args.date)
    fetch_acb_schedule(target, args.round)
