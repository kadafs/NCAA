import os
import json
import requests
import xml.etree.ElementTree as ET
import sys
# Add root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

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
    params = "statisticMode=PerGame&phaseTypeCode=RS&limit=400&seasonCode=E2025"
    
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

        # 3. Fetch Standings (The primary source for the team list and basic scoring)
        standings_url = "https://api-live.euroleague.net/v1/standings?seasonCode=E2025"
        standings_resp = requests.get(standings_url, headers={"User-Agent": "Mozilla/5.0"})
        standings_resp.raise_for_status()
        
        standings_root = ET.fromstring(standings_resp.content)
        merged_stats = {}
        
        # 4. Map Traditional Stats to teams (Needed for Pace calculation)
        trad_map = {}
        for t in trad_data.get('teams', []):
            trad_map[t['team']['name']] = t

        # Initialize from Standings and calculate Pace/Efficiency
        league_paces = []
        league_offs = []
        
        for team_el in standings_root.findall(".//team"):
            name_el = team_el.find('name')
            if name_el is None: continue
            name = name_el.text
            
            pts_favour = float(team_el.find('ptsfavour').text) if team_el.find('ptsfavour') is not None else 0
            pts_against = float(team_el.find('ptsagainst').text) if team_el.find('ptsagainst') is not None else 0
            total_games = float(team_el.find('totalgames').text) if team_el.find('totalgames') is not None else 0
            
            ppg = pts_favour / total_games if total_games > 0 else 0
            opp_ppg = pts_against / total_games if total_games > 0 else 0
            
            # Default Pace / Efficiency (will refine if trad stats exist)
            pace = 71.5
            off_eff = 110.0
            def_eff = 110.0
            
            t_stats = trad_map.get(name)
            if t_stats:
                # Formula: P = 0.96 * (FGA + TOV + 0.44 * FTA - ORB)
                fga = t_stats.get('twoPointersAttempted', 0) + t_stats.get('threePointersAttempted', 0)
                fta = t_stats.get('freeThrowsAttempted', 0)
                tov = t_stats.get('turnovers', 0)
                orb = t_stats.get('offensiveRebounds', 0)
                
                if fga > 0:
                    pace = 0.96 * (fga + tov + 0.44 * fta - orb)
                    if pace > 0:
                        off_eff = (ppg / pace) * 100
                        def_eff = (opp_ppg / pace) * 100
                        league_paces.append(pace)
                        league_offs.append(off_eff)

            merged_stats[name] = {
                "pts": ppg,
                "adj_off": off_eff,
                "adj_def": def_eff,
                "adj_t": pace,
                "code": team_el.find('code').text if team_el.find('code') is not None else "",
                "gp": int(total_games),
                "allowed": { "pts": opp_ppg },
                "four_factors": {
                    "efg": 52.0, "tov": 14.0, "orb": 30.0, "ftr": 28.0
                }
            }
        
        # Calculate League Averages for teams missing from trad stats (e.g. Paris, Dubai)
        avg_pace = sum(league_paces) / len(league_paces) if league_paces else 71.5
        avg_off = sum(league_offs) / len(league_offs) if league_offs else 110.0
        
        for name, data in merged_stats.items():
            if data["adj_t"] == 71.5: # If still default
                data["adj_t"] = avg_pace
                data["adj_off"] = (data["pts"] / avg_pace) * 100 if avg_pace > 0 else avg_off
                data["adj_def"] = (data["allowed"]["pts"] / avg_pace) * 100 if avg_pace > 0 else avg_off

        # 5. Overlay Advanced Stats for Four Factors
        for t in adv_data.get('teams', []):
            raw_name = t['team']['name']
            # Find the match in our merged_stats (initialized from standings)
            matched_name = find_team_in_dict(raw_name, merged_stats, BASKETBALL_ALIASES)
            
            if matched_name:
                merged_stats[matched_name]["four_factors"].update({
                    "efg": parse_pct(t.get('effectiveFieldGoalPercentage', 52.0)),
                    "tov": parse_pct(t.get('turnoversRatio', 14.0)),
                    "orb": parse_pct(t.get('offensiveReboundsPercentage', 30.0)),
                    "ftr": parse_pct(t.get('freeThrowsRate', 28.0))
                })
            
        # 6. Overlay FG3A from Traditional
        for raw_name, t_stats in trad_map.items():
            matched_name = find_team_in_dict(raw_name, merged_stats, BASKETBALL_ALIASES)
            if matched_name:
                merged_stats[matched_name]["fg3a"] = t_stats.get('fieldGoals3Attempted', 25.0)
        
        print(f"Processed stats for {len(merged_stats)} EuroLeague teams.")
        
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(merged_stats, f, indent=2)
            
        return merged_stats

    except Exception as e:
        print(f"Error fetching EuroLeague stats: {e}")
        return {}

if __name__ == "__main__":
    fetch_euro_team_stats()
