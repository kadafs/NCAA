
import json
import os
from datetime import datetime

def parse_date(date_str):
    if not date_str: return datetime.min
    # Try ISO format (API-Basketball)
    try: return datetime.strptime(date_str[:10], "%Y-%m-%d")
    except: pass
    # Try Proballers format
    try: return datetime.strptime(date_str, "%b %d, %Y")
    except: pass
    return datetime.min

def analyze_blending(league_id, slug, team_target):
    pro_path = f"data/historical/proballers_{slug}.json"
    api_path = f"data/historical/api_basketball_{league_id}.json"
    
    all_games = []
    
    # Load Proballers (ADV)
    if os.path.exists(pro_path):
        with open(pro_path, encoding='utf-8') as f:
            data = json.load(f)
            for g in data:
                p_date = parse_date(g.get('date', ''))
                clean = {
                    "date": p_date.strftime("%Y-%m-%d"),
                    "home_team": g.get("home_team", "").lower(),
                    "away_team": g.get("away_team", "").lower(),
                    "home_score": g.get("home_score"),
                    "away_score": g.get("away_score"),
                    "source": "ADV",
                    "_parsed_date": p_date
                }
                all_games.append(clean)
                
    # Load API (SRS)
    if os.path.exists(api_path):
        with open(api_path, encoding='utf-8') as f:
            data = json.load(f)
            for g in data:
                p_date = parse_date(g.get("date", ""))
                clean = {
                    "date": p_date.strftime("%Y-%m-%d"),
                    "home_team": g.get("home_team", "").lower(),
                    "away_team": g.get("away_team", "").lower(),
                    "home_score": g.get("home_score"),
                    "away_score": g.get("away_score"),
                    "source": "SRS",
                    "_parsed_date": p_date
                }
                all_games.append(clean)
                
    # Sort and Dedupe
    all_games.sort(key=lambda x: x["_parsed_date"])
    
    unique_games = {}
    team_target_lower = team_target.lower()
    
    for g in all_games:
        # Check if either team matches target
        if team_target_lower not in g['home_team'] and team_target_lower not in g['away_team']:
            continue
            
        # Semantic match: Date + Teams (sorted to handle home/away reversal if any)
        teams = sorted([g['home_team'], g['away_team']])
        gid = f"{g['date']}_{teams[0]}_{teams[1]}"
        
        if gid not in unique_games:
            unique_games[gid] = g
        else:
            # If we have an ADV version of the same game, it overwrites the SRS one
            if g['source'] == 'ADV':
                unique_games[gid] = g
                
    merged = list(unique_games.values())
    
    adv_count = sum(1 for g in merged if g['source'] == 'ADV')
    srs_count = sum(1 for g in merged if g['source'] == 'SRS')
    
    print(f"Team Analysis: {team_target}")
    print(f"Total Unique Games (Blended): {len(merged)}")
    print(f"Games with Advanced Metrics (ADV): {adv_count}")
    print(f"Games with only Basic Scores (SRS): {srs_count}")
    
    # Show an example of an ADV game
    example = next((g for g in merged if g['source'] == 'ADV'), None)
    if example:
        print("\n--- ADV Example ---")
        print(f"Match: {example['home_team']} vs {example['away_team']} ({example['date']})")
        print(f"Stats Available: {list(example.keys())}")

if __name__ == '__main__':
    analyze_blending(242, 'italy-serie-a2', 'Fortitudo Bologna')
