import json
import os
import glob
import difflib
from collections import defaultdict

# Load the existing map
CROSS_SOURCE_CANONICAL_MAP = {
    "KR Basket":           "KR Reykjavik",
    "Dabrowa Gornicza":    "MKS Dąbrowa Górnicza",
    "Zielona Gora":        "Enea Zastal Zielona Góra",
    "Torun":               "Twarde Pierniki Toruń",
    "Gornik Walbrzych":    "Górnik Trans.eu Walbrzych",
    "Ostrow Wielkopolski": "Stal Ostrów Wielkopolski",
}

def find_mismatches():
    historical_dir = "data/historical"
    api_files = glob.glob(os.path.join(historical_dir, "api_basketball_*.json"))
    proballers_files = glob.glob(os.path.join(historical_dir, "proballers_*.json"))
    flashscore_files = glob.glob(os.path.join(historical_dir, "flashscore_*.json"))
    
    api_teams = set()
    pro_teams = set()
    
    # Collect API/Flashscore teams (Score sources)
    for f_path in api_files + flashscore_files:
        try:
            with open(f_path, encoding="utf-8") as f:
                data = json.load(f)
                games = data if isinstance(data, list) else data.get("games", [])
                for g in games:
                    if g.get("home_team"): api_teams.add(g["home_team"])
                    if g.get("away_team"): api_teams.add(g["away_team"])
        except: pass
        
    # Collect Proballers teams (Stats source)
    for f_path in proballers_files:
        try:
            with open(f_path, encoding="utf-8") as f:
                data = json.load(f)
                games = data if isinstance(data, list) else data.get("games", [])
                for g in games:
                    if g.get("home_team"): pro_teams.add(g["home_team"])
                    if g.get("away_team"): pro_teams.add(g["away_team"])
        except: pass

    print(f"Total API/Score Teams: {len(api_teams)}")
    print(f"Total Proballers Teams: {len(pro_teams)}")
    
    # Teams in API that are NOT exactly in Proballers
    missing_in_pro = api_teams - pro_teams
    # Apply canonical map to see what remains missing
    remaining_missing = set()
    for t in missing_in_pro:
        if t not in CROSS_SOURCE_CANONICAL_MAP:
            remaining_missing.add(t)
            
    print(f"Teams missing exactly in Proballers: {len(remaining_missing)}")
    
    # Find near misses (Potential matches)
    suggestions = []
    for t in sorted(list(remaining_missing)):
        t_lower = t.lower()
        # Look for best match in Proballers
        best_match = None
        best_score = 0
        
        for p in pro_teams:
            p_lower = p.lower()
            
            # Rule 1: Substring
            if t_lower in p_lower or p_lower in t_lower:
                score = 0.95 # High confidence for substring
            else:
                score = difflib.SequenceMatcher(None, t_lower, p_lower).ratio()
            
            if score > best_score:
                best_score = score
                best_match = p
        
        if best_score > 0.6: # Lowered threshold to see everything
            suggestions.append({
                "api": t,
                "pro": best_match,
                "score": best_score
            })
            
    # Sort by score desc
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    
    print("\n--- POTENTIAL MAP SUGGESTIONS (Score 0.6 - 0.85) ---")
    print(f"{'API Name':<30} | {'Proballers Name':<30} | {'Score':<5}")
    print("-" * 70)
    for s in suggestions:
        if 0.6 <= s["score"] < 0.85:
            try:
                print(f"{s['api'][:30]:<30} | {s['pro'][:30]:<30} | {s['score']:.2f}")
            except UnicodeEncodeError:
                # Fallback for terminal encoding issues
                api_safe = s['api'].encode('ascii', 'ignore').decode('ascii')
                pro_safe = s['pro'].encode('ascii', 'ignore').decode('ascii')
                print(f"{api_safe[:30]:<30} | {pro_safe[:30]:<30} | {s['score']:.2f}")

if __name__ == "__main__":
    # Ensure stdout is utf-8 if possible
    import sys
    import io
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    find_mismatches()
