import requests
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fetch_acb_stats(round_id=5899):
    """
    Fetches ACB team standings and stats from api2.acb.com.
    """
    url = f"https://api2.acb.com/api/seasondata/Competition/standings?competitionId=1&editionId=90&roundId={round_id}"
    
    headers = {
        "Origin": "https://acb.com",
        "Referer": "https://acb.com/",
        "Accept": "application/json",
        "x-apikey": "0dd94928-6f57-4c08-a3bd-b1b2f092976e",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    }
    
    print(f"Fetching ACB stats for Round {round_id}...")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # Structure varies, assuming 'standings' or similar nested key
        # Based on user-provided preview, it's a list or dictionary with 'availableFilters' etc.
        # Actually the standings usually come in a 'data' or root level list.
        
        # Let's assume the user's successful request returned the standings list at a certain key.
        # If it's a list, we iterate.
        standings_list = data.get("standings", [])
        teams_list = data.get("teams", [])
        
        # Name mapping
        id_to_name = {t.get("id"): t.get("fullName") for t in teams_list}
        id_to_tri = {t.get("id"): t.get("abbreviatedName") for t in teams_list}
        
        combined_stats = {}
        for team in standings_list:
            t_id = team.get("teamId")
            name = id_to_name.get(t_id)
            if not name: continue
            
            # Map ACB fields to standardized ones
            # ACB uses 'loses' (sic), 'pointsFor', 'pointsAgainst'
            played = team.get("matchesPlayed", 0)
            combined_stats[name] = {
                "wins": team.get("wins", 0),
                "losses": team.get("loses", 0),
                "points_for": team.get("pointsFor", 0),
                "points_against": team.get("pointsAgainst", 0),
                "points_for_average": team.get("pointsFor", 0) / played if played > 0 else 0,
                "points_against_average": team.get("pointsAgainst", 0) / played if played > 0 else 0,
                "tricode": id_to_tri.get(t_id),
                # Efficiency stubs
                "offensive_rating": 110.0,
                "defensive_rating": 110.0,
                "pace": 74.0
            }
            
        print(f"Successfully processed stats for {len(combined_stats)} ACB teams.")
        
        # Save to data directory
        os.makedirs("data", exist_ok=True)
        with open("data/acb_stats.json", "w") as f:
            json.dump(combined_stats, f, indent=4)
            
        return combined_stats
        
    except Exception as e:
        print(f"Error fetching ACB stats: {e}")
        return {}

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, default=5899, help="ACB Round ID")
    args = parser.parse_args()
    fetch_acb_stats(args.round)
