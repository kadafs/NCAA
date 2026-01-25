import requests
import json
import os
import time

BASE_URL = "https://ncaa-api.henrygd.me"
# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

STATS_DIR = os.path.join(ROOT_DIR, "data", "stats")
CONSOLIDATED_FILE = os.path.join(ROOT_DIR, "data", "consolidated_stats.json")
INDIVIDUAL_DIR = os.path.join(ROOT_DIR, "data", "individual")
INDIVIDUAL_CONSOLIDATED = os.path.join(ROOT_DIR, "data", "individual_stats.json")
STANDINGS_FILE = os.path.join(ROOT_DIR, "data", "standings.json")

TEAM_STAT_IDS = {
    "scoring_offense": 145,
    "scoring_defense": 146,
    "scoring_margin": 147,
    "fg_pct": 148,
    "fg_pct_defense": 149,
    "ft_pct": 150,
    "rebound_margin": 151,
    "three_pt_pct": 152,
    "three_pt_pct_defense": 153,
    "turnover_margin": 519,
    "assist_turnover_ratio": 518
}

INDIVIDUAL_STAT_IDS = {
    "pts_pg": 136,
    "reb_pg": 137,
    "ast_pg": 140,
    "blk_pg": 138,
    "stl_pg": 139,
    "fg_made": 611,
    "fg_att": 618,
    "three_pt_made": 621,
    "three_pt_att": 624,
    "minutes_pg": 628
}

def fetch_stat(stat_type, stat_id):
    all_data = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        url = f"{BASE_URL}/stats/basketball-men/d1/current/{stat_type}/{stat_id}?page={page}"
        print(f"Fetching {url}...")
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                all_data.extend(data.get("data", []))
                total_pages = data.get("pages", 1)
                page += 1
            else:
                print(f"Error fetching page {page}: {response.status_code}")
                break
        except Exception as e:
            print(f"Exception: {e}")
            break
        time.sleep(0.05) # Be nice but slightly faster
    return all_data

def fetch_standings():
    url = f"{BASE_URL}/standings/basketball-men/d1/current"
    print(f"Fetching standings from {url}...")
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching standings: {e}")
    return []

def main():
    # Team Stats
    if not os.path.exists(STATS_DIR):
        os.makedirs(STATS_DIR)

    consolidated_team = {}
    for name, stat_id in TEAM_STAT_IDS.items():
        print(f"--- Fetching Team {name} (ID: {stat_id}) ---")
        data = fetch_stat("team", stat_id)
        consolidated_team[name] = data
        with open(f"{STATS_DIR}/{name}.json", "w") as f:
            json.dump(data, f, indent=2)
            
    with open(CONSOLIDATED_FILE, "w") as f:
        json.dump(consolidated_team, f, indent=2)
    
    # Individual Stats
    if not os.path.exists(INDIVIDUAL_DIR):
        os.makedirs(INDIVIDUAL_DIR)

    consolidated_indiv = {}
    for name, stat_id in INDIVIDUAL_STAT_IDS.items():
        print(f"--- Fetching Individual {name} (ID: {stat_id}) ---")
        data = fetch_stat("individual", stat_id)
        consolidated_indiv[name] = data
        with open(f"{INDIVIDUAL_DIR}/{name}.json", "w") as f:
            json.dump(data, f, indent=2)
            
    with open(INDIVIDUAL_CONSOLIDATED, "w") as f:
        json.dump(consolidated_indiv, f, indent=2)
        
    # Standings (for Conference/SoS)
    print("--- Fetching Standings ---")
    standings = fetch_standings()
    with open(STANDINGS_FILE, "w") as f:
        json.dump(standings, f, indent=2)
    
    print(f"Finished! Consolidated team data saved to {CONSOLIDATED_FILE}")
    print(f"Finished! Consolidated individual data saved to {INDIVIDUAL_CONSOLIDATED}")
    print(f"Finished! Standings saved to {STANDINGS_FILE}")

if __name__ == "__main__":
    main()
