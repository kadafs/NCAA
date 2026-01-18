import json
import os
import requests
from datetime import datetime

BASE_URL = "http://localhost:3000"
CONSOLIDATED_FILE = "data/consolidated_stats.json"

def load_stats():
    if not os.path.exists(CONSOLIDATED_FILE):
        return None
    with open(CONSOLIDATED_FILE, "r") as f:
        return json.load(f)

def fetch_scoreboard(year, month, day):
    url = f"{BASE_URL}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error fetching scoreboard: {e}")
    return None

def find_team(name, teams_dict):
    """Attempt to match scoreboard name to stats name."""
    if not name: return None
    if name in teams_dict: return name
    
    # Common variations
    standard_map = {
        "St. Mary's (CA)": "Saint Mary's (CA)",
        "St Mary's": "Saint Mary's (CA)",
        "Saint Mary's": "Saint Mary's (CA)",
        "UConn": "UConn", 
        "Ole Miss": "Ole Miss",
        "UPenn": "Penn"
    }
    if name in standard_map:
        return standard_map[name]

    # Fuzzy match
    name_low = name.lower()
    for t_name in teams_dict:
        t_low = t_name.lower()
        if name_low == t_low or name_low in t_low or t_low in name_low:
            return t_name
            
    return None

def run_advanced_predictions(date_str, stats_data):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Build team metrics
    teams = {}
    all_ppg, all_tempo, all_eff = [], [], []

    for key in stats_data:
        for entry in stats_data[key]:
            name = entry['Team']
            if name not in teams:
                teams[name] = {"games": int(entry.get('GM', 0))}
            
            if key == "scoring_offense":
                teams[name]['pts'] = float(entry.get('PTS', 0))
                teams[name]['ppg'] = float(entry.get('PPG', 0))
            elif key == "scoring_defense":
                teams[name]['opp_pts'] = float(entry.get('OPP PTS', 0))
                teams[name]['opp_ppg'] = float(entry.get('OPP PPG', 0))
            elif key == "fg_pct": teams[name]['fga'] = float(entry.get('FGA', 0))
            elif key == "ft_pct": teams[name]['fta'] = float(entry.get('FTA', 0))
            elif key == "turnover_margin": teams[name]['to'] = float(entry.get('TO', 0))

    # Calculate Efficiency/Tempo
    valid_teams = {}
    for name, stats in teams.items():
        if all(k in stats for k in ['fga', 'fta', 'to', 'pts', 'opp_pts']) and stats['games'] > 0:
            poss = 0.96 * (stats['fga'] + (0.44 * stats['fta']) + stats['to'])
            stats['possessions'] = poss
            stats['tempo'] = poss / stats['games']
            stats['off_eff'] = (stats['pts'] / poss) * 100
            stats['def_eff'] = (stats['opp_pts'] / poss) * 100
            
            all_ppg.append(stats['ppg'])
            all_tempo.append(stats['tempo'])
            all_eff.append(stats['off_eff'])
            valid_teams[name] = stats

    if not all_tempo:
        print("No valid stats found.")
        return

    avg_ppg = sum(all_ppg) / len(all_ppg)
    avg_tempo = sum(all_tempo) / len(all_tempo)
    avg_eff = sum(all_eff) / len(all_eff)

    # Fetch Scoreboard
    board = fetch_scoreboard(dt.year, dt.month, dt.day)
    if not board or 'games' not in board or not board['games']:
        print(f"No games found for {date_str}")
        return

    print(f"\n--- Advanced Predictions for {date_str} ---")
    
    predictions = []
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        teamA_raw = game['away']['names']['short']
        teamB_raw = game['home']['names']['short']
        
        nameA = find_team(teamA_raw, valid_teams)
        nameB = find_team(teamB_raw, valid_teams)

        if nameA and nameB:
            tA, tB = valid_teams[nameA], valid_teams[nameB]
            
            proj_tempo = (tA['tempo'] * tB['tempo']) / avg_tempo
            proj_ptsA = (tA['off_eff'] * tB['def_eff'] / avg_eff) * (proj_tempo / 100)
            proj_ptsB = (tB['off_eff'] * tA['def_eff'] / avg_eff) * (proj_tempo / 100)
            
            predictions.append({
                "matchup": f"{teamA_raw} @ {teamB_raw}",
                "score": f"{proj_ptsA:.1f} - {proj_ptsB:.1f}",
                "total": round(proj_ptsA + proj_ptsB, 1),
                "spread": round(proj_ptsA - proj_ptsB, 1)
            })

    # Sort and print
    for p in sorted(predictions, key=lambda x: x['total'], reverse=True):
        spread_str = f"Spread: {p['spread']}" if p['spread'] < 0 else f"Spread: +{p['spread']}"
        print(f"{p['matchup']:35} | Proj: {p['score']:12} | Total: {p['total']:5.1f} | {spread_str}")

if __name__ == "__main__":
    stats = load_stats()
    if stats:
        for date in ["2026-01-10", "2026-01-11", "2026-01-12"]:
            run_advanced_predictions(date, stats)
    else:
        print("Stats not loaded.")
