import requests
import json
import os
import sys
import time

# Path injection for root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

BASE_URL = "https://ncaa-api-w2ry.onrender.com"
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

from utils.ssl_adapter import get_robust_session

# Use centralized robust session
http = get_robust_session(retries=3)

# Generic headers to improve acceptance
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

def fetch_stat(stat_id, is_individual=False):
    """
    Fetches statistical data from the centralized API.
    Correct URL construction for NCAA.com scraper:
    Team: /stats/basketball-men/d1/current/team/{id}
    Individual: /stats/basketball-men/d1/current/individual/{id}
    """
    all_data = []
    page = 1
    total_pages = 1
    
    type_segment = "individual" if is_individual else "team"
    
    while page <= total_pages:
        url = f"{BASE_URL}/stats/basketball-men/d1/current/{type_segment}/{stat_id}?page={page}"
        print(f"Fetching {url}")
        try:
            response = http.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                data = response.json()
                all_data.extend(data.get("data", []))
                total_pages = data.get("pages", 1)
                page += 1
            else:
                print(f"Error fetching page {page}: {response.status_code}")
                break
        except requests.exceptions.SSLError as ssl_err:
            print(f"SSL Error: {ssl_err}")
            print("Retrying with verify=False (Security Warning)")
            try:
                response = http.get(url, headers=HEADERS, timeout=30, verify=False)
                if response.status_code == 200:
                    data = response.json()
                    all_data.extend(data.get("data", []))
                    total_pages = data.get("pages", 1)
                    page += 1
                    continue
            except Exception as e2:
                print(f"Fallback also failed: {e2}")
                break
        except Exception as e:
            print(f"Exception: {e}")
            break
        time.sleep(0.05) 
    return all_data

def fetch_standings():
    url = f"{BASE_URL}/standings/basketball-men/d1"
    print(f"Fetching {url}")
    try:
        response = http.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching standings: {response.status_code}")
            return None
    except requests.exceptions.SSLError as ssl_err:
        print(f"SSL Error: {ssl_err}")
        print("Retrying with verify=False (Security Warning)")
        try:
            response = http.get(url, headers=HEADERS, timeout=30, verify=False)
            if response.status_code == 200:
                return response.json()
        except Exception as e2:
            print(f"Fallback also failed: {e2}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def main():
    # 1. Fetch standings
    standings = fetch_standings()
    if standings:
        os.makedirs(os.path.dirname(STANDINGS_FILE), exist_ok=True)
        with open(STANDINGS_FILE, "w") as f:
            json.dump(standings, f, indent=2)
        print(f"Saved standings to {STANDINGS_FILE}")

    # 2. Fetch team stats
    consolidated_team = {}
    os.makedirs(STATS_DIR, exist_ok=True)
    
    for stat_name, stat_id in TEAM_STAT_IDS.items():
        data = fetch_stat(stat_id, is_individual=False)
        if data:
            output_path = os.path.join(STATS_DIR, f"{stat_name}.json")
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved {stat_name} to {output_path}")
            
            # Basic consolidation
            for entry in data:
                team = entry.get("Team")
                if team:
                    if team not in consolidated_team:
                        consolidated_team[team] = {}
                    # Add stats
                    for k, v in entry.items():
                        if k not in ["Team", "Conference", "Rank"]:
                            consolidated_team[team][k] = v
                            
    if consolidated_team:
        with open(CONSOLIDATED_FILE, "w") as f:
            json.dump(consolidated_team, f, indent=2)
        print(f"Saved consolidated team stats to {CONSOLIDATED_FILE}")

    # 3. Fetch individual stats (TEMPORARILY DISABLED TO PREVENT TIMEOUTS)
    # Individual stats take ~7 minutes to fetch and aren't used in production totals yet.
    """
    consolidated_ind = {}
    os.makedirs(INDIVIDUAL_DIR, exist_ok=True)
    
    for stat_name, stat_id in INDIVIDUAL_STAT_IDS.items():
        data = fetch_stat(stat_id, is_individual=True)
        if data:
            output_path = os.path.join(INDIVIDUAL_DIR, f"{stat_name}.json")
            with open(output_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Saved individual {stat_name} to {output_path}")
            
            # Individual consolidation
            for entry in data:
                player = entry.get("Player")
                if player:
                    if player not in consolidated_ind:
                        consolidated_ind[player] = {"Team": entry.get("Team")}
                    for k, v in entry.items():
                        if k not in ["Player", "Team", "Rank"]:
                            consolidated_ind[player][f"{stat_name}_{k}"] = v

    if consolidated_ind:
        with open(INDIVIDUAL_CONSOLIDATED, "w") as f:
            json.dump(consolidated_ind, f, indent=2)
        print(f"Saved consolidated individual stats to {INDIVIDUAL_CONSOLIDATED}")
    """

if __name__ == "__main__":
    main()
