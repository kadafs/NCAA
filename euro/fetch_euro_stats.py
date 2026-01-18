import os
import json
import requests
import xml.etree.ElementTree as ET

# Base paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
STATS_FILE = os.path.join(ROOT_DIR, "data", "euro_stats.json")

def parse_pct(val):
    if isinstance(val, str) and "%" in val:
        try:
            return float(val.replace("%", ""))
        except:
            return 0.0
    return float(val) if val else 0.0

def fetch_euro_team_stats():
    print("Fetching EuroLeague team statistics (v3 advanced + traditional + standings)...")
    
    base_url = "https://api-live.euroleague.net/v3/competitions/E/statistics/teams"
    params = "statisticMode=PerGame&phaseTypeCode=RS&limit=400"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    try:
        # 1. Fetch Advanced Stats (Off/Def Ratings, Four Factors)
        adv_resp = requests.get(f"{base_url}/advanced?{params}", headers=headers)
        adv_resp.raise_for_status()
        adv_data = adv_resp.json()
        
        # 2. Fetch Traditional Stats (Points, 3PA)
        trad_resp = requests.get(f"{base_url}/traditional?{params}", headers=headers)
        trad_resp.raise_for_status()
        trad_data = trad_resp.json()

        # 3. Fetch Standings (for Points Against)
        standings_url = "https://api-live.euroleague.net/v1/standings?seasonCode=E2024"
        standings_resp = requests.get(standings_url, headers={"User-Agent": "Mozilla/5.0"})
        standings_resp.raise_for_status()
        
        standings_root = ET.fromstring(standings_resp.content)
        opp_stats = {}
        for team_el in standings_root.findall(".//team"):
            team_name = team_el.find('name').text
            pts_against = float(team_el.find('ptsagainst').text)
            total_games = float(team_el.find('totalgames').text)
            opp_stats[team_name] = pts_against / total_games if total_games > 0 else 0
        
        merged_stats = {}
        
        # Process Advanced
        for t in adv_data.get('teams', []):
            name = t['team']['name']
            merged_stats[name] = {
                "adj_off": t.get('offensiveRating', 110.0),
                "adj_def": t.get('defensiveRating', 110.0),
                "adj_t": t.get('possessions', 72.0),
                "code": t['team']['code'],
                "four_factors": {
                    "efg": parse_pct(t.get('effectiveFieldGoalPercentage', 50.0)),
                    "tov": parse_pct(t.get('turnoversRatio', 15.0)),
                    "orb": parse_pct(t.get('offensiveReboundsPercentage', 30.0)),
                    "ftr": parse_pct(t.get('freeThrowsRate', 25.0))
                }
            }
            
        # Merge Traditional and Standing Stats
        for t in trad_data.get('teams', []):
            name = t['team']['name']
            if name in merged_stats:
                merged_stats[name].update({
                    "pts": t.get('pointsScored', 80.0),
                    "fg3a": t.get('fieldGoals3Attempted', 25.0),
                    "gp": t.get('gamesPlayed', 0),
                    "allowed": {
                        "pts": opp_stats.get(name, 80.0)
                    }
                })
        
        print(f"Processed stats for {len(merged_stats)} EuroLeague teams.")
        
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(merged_stats, f, indent=2)
            
        return merged_stats

    except Exception as e:
        print(f"Error fetching EuroLeague stats: {e}")
        return {}

if __name__ == "__main__":
    fetch_euro_team_stats()
