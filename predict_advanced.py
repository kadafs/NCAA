import json
import os
import requests
from datetime import datetime

# Script 1: General Accuracy Model
# Features: Home-Court Advantage, Conference-based Strength of Schedule (SoS),
# Weighted Efficiency and Four Factors.

BASE_URL = "http://localhost:3000"
TEAM_STATS_FILE = "data/consolidated_stats.json"
STANDINGS_FILE = "data/standings.json"

# Conference Rankings Proxy (Higher = Stronger Conference)
# Based on historical/NET context
CONF_QUALITY = {
    "Big 12": 1.15, "SEC": 1.12, "Big Ten": 1.10, "ACC": 1.08, "Big East": 1.08,
    "Mountain West": 1.04, "Pac-12": 1.02, "American": 1.00, "WCC": 0.98,
    "Atlantic 10": 0.96, "Missouri Valley": 0.94, "Sun Belt": 0.92
}
DEFAULT_QUALITY = 0.85

HOME_ADVANTAGE = 3.5

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def find_team(name, teams_dict):
    if not name: return None
    if name in teams_dict: return name
    # Common mapping for inconsistent naming
    standard_map = {
        "St. Mary's (CA)": "Saint Mary's (CA)",
        "St Mary's": "Saint Mary's (CA)",
        "Saint Mary's": "Saint Mary's (CA)",
        "UConn": "UConn", "Ole Miss": "Ole Miss", "UPenn": "Penn"
    }
    if name in standard_map: return standard_map[name]
    name_low = name.lower()
    for t_name in teams_dict:
        t_low = t_name.lower()
        if name_low == t_low or name_low in t_low or t_low in name_low:
            return t_name
    return None

def get_team_metrics(stats_data, standings_data):
    # Map schools to conferences
    school_to_conf = {}
    for conf_group in standings_data.get('data', []):
        conf_name = conf_group['conference']
        for team in conf_group['standings']:
            school_to_conf[team['School']] = conf_name

    teams = {}
    for key in stats_data:
        for entry in stats_data[key]:
            name = entry['Team']
            if name not in teams: teams[name] = {"games": int(entry.get('GM', 0))}
            
            if key == "scoring_offense":
                teams[name]['pts'] = float(entry.get('PTS', 0))
                teams[name]['ppg'] = float(entry.get('PPG', 0))
            elif key == "scoring_defense":
                teams[name]['opp_pts'] = float(entry.get('OPP PTS', 0))
            elif key == "fg_pct": 
                teams[name]['fga'] = float(entry.get('FGA', 0))
                teams[name]['efg'] = float(entry.get('FG%', 0)) # Using FG% as proxy if eFG unavailable
            elif key == "ft_pct": teams[name]['fta'] = float(entry.get('FTA', 0))
            elif key == "turnover_margin": teams[name]['to'] = float(entry.get('TO', 0))
            elif key == "rebound_margin": teams[name]['reb_margin'] = float(entry.get('REB MARGIN', 0))

    valid_teams = {}
    all_tempo, all_off_eff, all_def_eff = [], [], []

    for name, stats in teams.items():
        if all(k in stats for k in ['fga', 'fta', 'to', 'pts', 'opp_pts']) and stats['games'] > 0:
            # Estimate possessions
            poss = 0.96 * (stats['fga'] + (0.44 * stats['fta']) + stats['to'])
            stats['tempo'] = poss / stats['games']
            
            # Apply SoS weighting to efficiency
            conf = school_to_conf.get(name, "Other")
            weight = CONF_QUALITY.get(conf, DEFAULT_QUALITY)
            
            stats['raw_off_eff'] = (stats['pts'] / poss) * 100
            stats['raw_def_eff'] = (stats['opp_pts'] / poss) * 100
            
            # Weighted Efficiency
            stats['off_eff'] = stats['raw_off_eff'] * weight
            stats['def_eff'] = stats['raw_def_eff'] / weight # Defense is better if weighted higher
            
            all_tempo.append(stats['tempo'])
            all_off_eff.append(stats['off_eff'])
            all_def_eff.append(stats['def_eff'])
            valid_teams[name] = stats
            
    return valid_teams, sum(all_tempo)/len(all_tempo), sum(all_off_eff)/len(all_off_eff), sum(all_def_eff)/len(all_def_eff)

def predict_game(away_raw, home_raw, metrics, league_avgs):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    avg_tempo, avg_off, avg_def = league_avgs
    
    # 1. Tempo Adjustment
    proj_tempo = (tA['tempo'] * tH['tempo']) / avg_tempo
    
    # 2. Adjusted Efficiency with Home Court Advantage
    # Away Team Offense vs Home Team Defense
    effA = (tA['off_eff'] * tH['def_eff']) / avg_off
    # Home Team Offense vs Away Team Defense
    effH = (tH['off_eff'] * tA['def_eff']) / avg_off
    
    scoreA = (effA * proj_tempo) / 100
    scoreH = ((effH * proj_tempo) / 100) + HOME_ADVANTAGE
    
    return {
        "away": away_raw, "home": home_raw,
        "scoreA": round(scoreA, 1), "scoreH": round(scoreH, 1),
        "total": round(scoreA + scoreH, 1),
        "spread": round(scoreH - scoreA, 1)
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    standings_data = load_json(STANDINGS_FILE)
    if not stats_data or not standings_data: 
        print("Data files missing.")
        return

    metrics, avg_tempo, avg_off, avg_def = get_team_metrics(stats_data, standings_data)
    league_avgs = (avg_tempo, avg_off, avg_def)

    # Preview Predictions for selected matchups
    matchups = [
        ("Arizona", "TCU"), ("Alabama", "Texas"), ("Villanova", "Marquette"), ("Duke", "NC State")
    ]
    
    print(f"{'Matchup':<40} | {'Proj Score':<15} | {'Total':<10} | {'Spread':<10}")
    print("-" * 85)
    for away, home in matchups:
        res = predict_game(away, home, metrics, league_avgs)
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            score_str = f"{res['scoreA']} - {res['scoreH']}"
            print(f"{match_str:<40} | {score_str:<15} | {res['total']:<10} | {res['spread']:<10}")

if __name__ == "__main__":
    main()
