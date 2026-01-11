import json
import os
import requests
from datetime import datetime

BASE_URL = "http://localhost:3000"
TEAM_STATS_FILE = "data/consolidated_stats.json"
INDIV_STATS_FILE = "data/individual_stats.json"

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def find_team(name, teams_dict):
    if not name: return None
    if name in teams_dict: return name
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

def get_team_metrics(stats_data):
    teams = {}
    all_ppg, all_tempo, all_eff = [], [], []
    for key in stats_data:
        for entry in stats_data[key]:
            name = entry['Team']
            if name not in teams: teams[name] = {"games": int(entry.get('GM', 0))}
            if key == "scoring_offense":
                teams[name]['pts'] = float(entry.get('PTS', 0))
                teams[name]['ppg'] = float(entry.get('PPG', 0))
            elif key == "scoring_defense":
                teams[name]['opp_pts'] = float(entry.get('OPP PTS', 0))
            elif key == "fg_pct": teams[name]['fga'] = float(entry.get('FGA', 0))
            elif key == "ft_pct": teams[name]['fta'] = float(entry.get('FTA', 0))
            elif key == "turnover_margin": teams[name]['to'] = float(entry.get('TO', 0))

    valid_teams = {}
    for name, stats in teams.items():
        if all(k in stats for k in ['fga', 'fta', 'to', 'pts', 'opp_pts']) and stats['games'] > 0:
            poss = 0.96 * (stats['fga'] + (0.44 * stats['fta']) + stats['to'])
            stats['tempo'] = poss / stats['games']
            stats['off_eff'] = (stats['pts'] / poss) * 100
            stats['def_eff'] = (stats['opp_pts'] / poss) * 100
            all_ppg.append(stats['ppg'])
            all_tempo.append(stats['tempo'])
            all_eff.append(stats['off_eff'])
            valid_teams[name] = stats
    
    return valid_teams, sum(all_ppg)/len(all_ppg), sum(all_tempo)/len(all_tempo), sum(all_eff)/len(all_eff)

def predict_matchup_props(teamA_raw, teamB_raw, team_metrics, avg_vals, indiv_stats):
    nameA = find_team(teamA_raw, team_metrics)
    nameB = find_team(teamB_raw, team_metrics)
    if not nameA or not nameB: return
    
    tA, tB = team_metrics[nameA], team_metrics[nameB]
    avg_ppg, avg_tempo, avg_eff = avg_vals
    
    proj_tempo = (tA['tempo'] * tB['tempo']) / avg_tempo
    proj_ptsA = (tA['off_eff'] * tB['def_eff'] / avg_eff) * (proj_tempo / 100)
    proj_ptsB = (tB['off_eff'] * tA['def_eff'] / avg_eff) * (proj_tempo / 100)
    
    factorA = proj_ptsA / tA['ppg']
    factorB = proj_ptsB / tB['ppg']
    tempo_factor = proj_tempo / avg_tempo

    print(f"\n=== Player Props: {teamA_raw} @ {teamB_raw} ===")
    print(f"Projected Score: {proj_ptsA:.1f} - {proj_ptsB:.1f} | Tempo: {proj_tempo:.1f}")
    
    for team_name, factor, raw_name in [(nameA, factorA, teamA_raw), (nameB, factorB, teamB_raw)]:
        print(f"\n--- {raw_name} Players ---")
        players = {}
        # Collect player averages
        for cat, entries in indiv_stats.items():
            for p in entries:
                if p['Team'] == team_name:
                    pname = p['Name']
                    if pname not in players: players[pname] = {}
                    if cat == "pts_pg": players[pname]['pts'] = float(p.get('PPG', 0))
                    elif cat == "reb_pg": players[pname]['reb'] = float(p.get('RPG', 0))
                    elif cat == "ast_pg": players[pname]['ast'] = float(p.get('APG', 0))
                    elif cat == "three_pt_made": players[pname]['triples'] = float(p.get('3FG', 0))
                    elif cat == "blk_pg": players[pname]['blk'] = float(p.get('BPG', 0))
                    elif cat == "stl_pg": players[pname]['stl'] = float(p.get('SPG', 0))

        # Filter and project top players (at least 8 PPG)
        for name, p_stats in players.items():
            if p_stats.get('pts', 0) > 8:
                proj_pts = p_stats['pts'] * factor
                proj_reb = p_stats.get('reb', 0) * tempo_factor
                proj_ast = p_stats.get('ast', 0) * factor
                print(f"{name:20} | Proj Pts: {proj_pts:4.1f} | Reb: {proj_reb:3.1f} | Ast: {proj_ast:3.1f}")

def main():
    team_data = load_json(TEAM_STATS_FILE)
    indiv_data = load_json(INDIV_STATS_FILE)
    if not team_data or not indiv_data:
        print("Data files missing.")
        return
        
    metrics, avg_ppg, avg_tempo, avg_eff = get_team_metrics(team_data)
    
    # Feature matchups for Jan 10-12
    matchups = [
        ("Arizona", "TCU"),
        ("Alabama", "Texas"),
        ("Villanova", "Marquette"),
        ("Duke", "NC State")
    ]
    
    for a, b in matchups:
        predict_matchup_props(a, b, metrics, (avg_ppg, avg_tempo, avg_eff), indiv_data)

if __name__ == "__main__":
    main()
