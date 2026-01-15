import json
import os
import requests
from datetime import datetime

# Script 2: Over/Under Focused Model
# Features: Offensive Rebounding (Possession Resets), 3PT Regression,
# Late Game Fouling (Free Throw Trap), and Tempo Archetypes.

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
TEAM_STATS_FILE = "data/consolidated_stats.json"

def fetch_scoreboard(year, month, day):
    for base in BASE_URLS:
        url = f"{base}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except:
            continue
    return None

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

def get_total_metrics(stats_data):
    teams = {}
    all_tempo, all_off_eff = [], []
    
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
            elif key == "ft_pct": teams[name]['ft_pct'] = float(entry.get('FT%', 0))
            elif key == "turnover_margin": teams[name]['to'] = float(entry.get('TO', 0))
            elif key == "rebound_margin": teams[name]['reb_margin'] = float(entry.get('REB MARGIN', 0))
            elif key == "three_pt_pct": teams[name]['three_pct'] = float(entry.get('3FG%', 0))
            elif key == "assist_turnover_ratio": teams[name]['ast_to_ratio'] = float(entry.get('RATIO', 0))

    valid_teams = {}
    for name, stats in teams.items():
        if all(k in stats for k in ['fga', 'pts', 'opp_pts', 'ft_pct', 'reb_margin']) and stats['games'] > 0:
            # Basic possession estimate
            # Since we don't have exact FTA/TO for all, we estimate
            # possessions = FGA + 0.44 * FTA + TO
            # We proxy FTA as 0.25 * PPG and TO as 12 per game
            est_fta = stats['ppg'] * 0.25 * stats['games']
            est_to = 12 * stats['games']
            poss = 0.96 * (stats['fga'] + (0.44 * est_fta) + est_to)
            
            stats['tempo'] = poss / stats['games']
            stats['off_eff'] = (stats['pts'] / poss) * 100
            stats['def_eff'] = (stats['opp_pts'] / poss) * 100
            
            all_tempo.append(stats['tempo'])
            all_off_eff.append(stats['off_eff'])
            valid_teams[name] = stats
            
    return valid_teams, sum(all_tempo)/len(all_tempo), sum(all_off_eff)/len(all_off_eff)

def predict_total(away_raw, home_raw, metrics, league_avgs):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    avg_tempo, avg_eff = league_avgs[0], league_avgs[1]
    
    # 1. Base Projection
    proj_tempo = (tA['tempo'] * tH['tempo']) / avg_tempo
    effA = (tA['off_eff'] * tH['def_eff']) / avg_eff
    effH = (tH['off_eff'] * tA['def_eff']) / avg_eff
    
    base_scoreA = (effA * proj_tempo) / 100
    base_scoreH = (effH * proj_tempo) / 100
    
    # 2. Offensive Rebounding Flip (Possession Resets)
    # High rebound margin teams get +0.5 to +2.0 points
    reb_bonusA = max(0, tA['reb_margin'] * 0.2)
    reb_bonusH = max(0, tH['reb_margin'] * 0.2)
    
    # 3. 3PT Regression (Regression to Mean)
    # If a team shoots > 38%, they likely underperform. If < 30%, they likely overperform.
    regA = (34.0 - tA['three_pct']) * 0.1
    regH = (34.0 - tH['three_pct']) * 0.1
    
    # 4. Late Game FT Trap
    # If the score is close, teams foul. Teams with high FT% score more in this phase.
    ft_trap = 0
    if abs(base_scoreA - base_scoreH) < 5:
        ft_trap = (tA['ft_pct'] + tH['ft_pct']) / 50.0 # approx 2-4 points extra
        
    finalA = base_scoreA + reb_bonusA + regA + (ft_trap / 2)
    finalH = base_scoreH + reb_bonusH + regH + (ft_trap / 2)
    
    return {
        "away": away_raw, "home": home_raw,
        "base_total": round(base_scoreA + base_scoreH, 1),
        "adj_total": round(finalA + finalH, 1),
        "diff": round((finalA + finalH) - (base_scoreA + base_scoreH), 1),
        "logic": f"Reb: +{reb_bonusA+reb_bonusH:.1f} | 3PT Reg: {regA+regH:.1f} | FT Trap: +{ft_trap:.1f}"
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    if not stats_data: return
    
    metrics, avg_tempo, avg_eff = get_total_metrics(stats_data)
    
    # Use current date
    now = datetime.now()
    print(f"\n--- Totals Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Base Total':<12} | {'Adj Total':<12} | {'Diff':<8}")
    print("-" * 85)
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away = game['away']['names']['short']
        home = game['home']['names']['short']
        
        res = predict_total(away, home, metrics, (avg_tempo, avg_eff))
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            print(f"{match_str:<40} | {res['base_total']:<12} | {res['adj_total']:<12} | {res['diff']:<8}")
            print(f"  > Log: {res['logic']}")

if __name__ == "__main__":
    main()
