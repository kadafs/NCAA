import json
import os
import glob
import difflib

def find_nbl1_mismatches():
    # 1. Load all API teams from NBL1 leagues (207-216)
    api_teams = set()
    prediction_files = glob.glob("data/basketball/universal_predictions_*.json")
    nbl1_leagues = {207, 208, 209, 210, 211, 212, 213, 214, 215, 216}
    
    for f_path in prediction_files:
        try:
            with open(f_path, encoding="utf-8") as f:
                data = json.load(f)
                preds = data.get("predictions", [])
                for p in preds:
                    if p.get("league_id") in nbl1_leagues:
                        if p.get("home_team"): api_teams.add(p["home_team"])
                        if p.get("away_team"): api_teams.add(p["away_team"])
        except: pass

    # 2. Load all Official Scraper teams
    off_teams = set()
    off_files = glob.glob("data/historical/nbl1_official_*.json")
    for f_path in off_files:
        try:
            with open(f_path, encoding="utf-8") as f:
                data = json.load(f)
                for g in data:
                    if g.get("home_team"): off_teams.add(g["home_team"])
                    if g.get("away_team"): off_teams.add(g["away_team"])
        except: pass

    print(f"API Teams: {len(api_teams)}")
    print(f"Official Teams: {len(off_teams)}")

    # 3. Find mismatches
    print("\n--- NBL1 TEAM NAME COMPARISON ---")
    print(f"{'API Team':<30} | {'Official Team':<30} | {'Ratio':<5}")
    print("-" * 70)
    
    matches = []
    unmatched_api = sorted(list(api_teams))
    
    for api_t in unmatched_api:
        if api_t in off_teams:
            continue # Exact match
            
        # Fuzzy match
        best_off = None
        best_ratio = 0
        for off_t in off_teams:
            # Substring match (high confidence)
            if api_t.lower() in off_t.lower() or off_t.lower() in api_t.lower():
                ratio = 0.99
            else:
                ratio = difflib.SequenceMatcher(None, api_t.lower(), off_t.lower()).ratio()
            
            if ratio > best_ratio:
                best_ratio = ratio
                best_off = off_t
        
        if best_off:
            matches.append((api_t, best_off, best_ratio))
            
    # Sort by ratio
    matches.sort(key=lambda x: x[2], reverse=True)
    for api, off, ratio in matches:
        print(f"{api:<30} | {off:<30} | {ratio:.2f}")

if __name__ == "__main__":
    find_nbl1_mismatches()
