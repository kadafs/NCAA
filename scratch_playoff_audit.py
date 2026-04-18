import json
import urllib.request
import statistics
from datetime import datetime

API_KEY = "3c3f6f1c79e735e07a6d895513d6aabf"
LEAGUES = [
    (117, "2025-2026", "SPAIN — ACB"),
    (211, "2025-2026", "AUSTRALIA — NBL1 CENTRAL WOMEN")
]

def is_playoff(stage):
    if not stage:
        return False
    s = str(stage).lower()
    return any(k in s for k in ['final', 'place', 'playoff', 'championship'])

print("Auditing Volatility (With vs Without Playoffs)\n" + "="*60)

for league_id, season, name in LEAGUES:
    url = f"https://v1.basketball.api-sports.io/fixtures?league={league_id}&season={season}"
    req = urllib.request.Request(url, headers={
        'x-apisports-key': API_KEY,
        'Accept': 'application/json'
    })
    
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Failed to fetch {name}: {e}")
        continue
        
    fixtures = data.get("response", [])
    if not fixtures:
        continue
        
    all_team_totals = {}       # { team_name: [totals] }
    reg_team_totals = {}       # { team_name: [totals] }
    
    for fix in fixtures:
        h_score = fix.get("scores", {}).get("home", {}).get("total")
        a_score = fix.get("scores", {}).get("away", {}).get("total")
        if h_score is None or a_score is None:
            continue
            
        status = fix.get("status", {}).get("short")
        # skip forfeits/awarded
        if status in ("AW", "AWD", "WO", "FT:AW") or (h_score==0 and a_score==20) or (h_score==20 and a_score==0):
            continue
            
        total = int(h_score) + int(a_score)
        home = fix["teams"]["home"]["name"]
        away = fix["teams"]["away"]["name"]
        stage = fix.get("league", {}).get("stage", "")
        
        playoff = is_playoff(stage)
        
        for t in [home, away]:
            if t not in all_team_totals:
                all_team_totals[t] = []
                reg_team_totals[t] = []
            all_team_totals[t].append(total)
            if not playoff:
                reg_team_totals[t].append(total)
                
    print(f"\n{name} (ID {league_id})")
    print(f"{'Team':<30} | {'ALL (inc. Playoffs)':<20} | {'REG SEASON ONLY':<20} | Diff")
    print("-" * 80)
    
    for team, all_scores in sorted(all_team_totals.items()):
        reg_scores = reg_team_totals[team]
        
        all_std = statistics.pstdev(all_scores) if len(all_scores) > 1 else 0
        reg_std = statistics.pstdev(reg_scores) if len(reg_scores) > 1 else 0
        diff = all_std - reg_std
        
        all_str = f"σ {all_std:>4.1f} ({len(all_scores):>2}g)"
        reg_str = f"σ {reg_std:>4.1f} ({len(reg_scores):>2}g)"
        diff_str = f"{diff:>+5.1f}"
        
        # Only print teams where playoffs changed the classification (crosses 14.8 or 16.6 boundaries)
        # or if the difference is > 1.0
        c1 = "Green" if all_std < 14.8 else "Blue" if all_std <= 16.6 else "None"
        c2 = "Green" if reg_std < 14.8 else "Blue" if reg_std <= 16.6 else "None"
        
        if c1 != c2 or abs(diff) > 1.5:
            print(f"{team[:29]:<30} | {all_str:<20} | {reg_str:<20} | {diff_str}  [{c1}->{c2}]")

