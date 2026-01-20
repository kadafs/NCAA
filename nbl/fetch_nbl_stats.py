import requests
import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fetch_nbl_stats():
    """
    Fetches NBL team stats and standings from the Rosetta API.
    """
    stats_url = "https://prod.rosetta.nbl.com.au/get/nbl/team/stats/for/season/2025/regular"
    standings_url = "https://prod.rosetta.nbl.com.au/get/nbl/standings/2025/regular"
    
    headers = {
        "Origin": "https://www.nbl.com.au",
        "Referer": "https://www.nbl.com.au/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36"
    }
    
    print("Fetching NBL stats and standings...")
    try:
        # 1. Fetch Stats (Efficiency)
        res_stats = requests.get(stats_url, headers=headers)
        res_stats.raise_for_status()
        stats_data = res_stats.json().get("data", [])
        
        # 2. Fetch Standings (Record/Defense)
        res_standings = requests.get(standings_url, headers=headers)
        res_standings.raise_for_status()
        standings_data = res_standings.json().get("data", [])
        
        # Merge data
        combined_stats = {}
        
        for team in stats_data:
            team_obj = team.get("team", {})
            name = team_obj.get("name")
            if not name: continue
            
            # Basic efficiency/pace markers
            combined_stats[name] = {
                "offensive_rating": team.get("offensive_rating"),
                "defensive_rating": team.get("defensive_rating"),
                "pace": team.get("pace"),
                "field_goals_percentage": team.get("field_goals_percentage"),
                "three_pointers_percentage": team.get("three_pointers_percentage"),
                "free_throws_percentage": team.get("free_throws_percentage"),
                "rebounds_average": team.get("rebounds_average"),
                "assists_average": team.get("assists_average"),
                "turnovers_average": team.get("turnovers_average")
            }
            
        for team in standings_data:
            team_obj = team.get("team", {})
            name = team_obj.get("name")
            if name in combined_stats:
                combined_stats[name].update({
                    "wins": team.get("won"),
                    "losses": team.get("lost"),
                    "points_for": team.get("points_for"),
                    "points_against": team.get("points_against"),
                    "points_for_average": team.get("points_for") / team.get("played") if team.get("played") > 0 else 0,
                    "points_against_average": team.get("points_against") / team.get("played") if team.get("played") > 0 else 0
                })
        
        print(f"Successfully processed stats for {len(combined_stats)} NBL teams.")
        
        # Save to data directory
        os.makedirs("data", exist_ok=True)
        with open("data/nbl_stats.json", "w") as f:
            json.dump(combined_stats, f, indent=4)
            
        return combined_stats
        
    except Exception as e:
        print(f"Error fetching NBL stats: {e}")
        return {}

if __name__ == "__main__":
    fetch_nbl_stats()
