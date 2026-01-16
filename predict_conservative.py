import json
import os
import requests
import zoneinfo
from datetime import datetime

# Script 3: Conservative / Pessimistic Model
# Goal: Address "over-optimistic" scoring by applying aggressive penalties
# to visiting teams and mid-majors playing "up".

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
TEAM_STATS_FILE = "data/consolidated_stats.json"
STANDINGS_FILE = "data/standings.json"

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

ROAD_PENALTY = 0.95 # -5% efficiency for visiting team
TEMPO_DRAG = 0.65   # The slower team controls 65% of the pace

# Conferences considered "Power" or high-tier to avoid deflation
POWER_CONFS = ["Big 12", "SEC", "Big Ten", "ACC", "Big East", "Mountain West"]

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def find_team(name, teams_dict):
    if not name: return None
    name_low = name.lower()
    for t_name in teams_dict:
        t_low = t_name.lower()
        if name_low == t_low or name_low in t_low or t_low in name_low:
            return t_name
    return None

def get_pessimistic_metrics(stats_data, standings_data):
    # Map schools to conferences
    school_to_conf = {}
    data_list = standings_data.get('data', []) if isinstance(standings_data, dict) else []
    for conf_group in data_list:
        for team in conf_group['standings']:
            school_to_conf[team['School']] = conf_group['conference']

    teams = {}
    for key in stats_data:
        for entry in stats_data[key]:
            name = entry['Team']
            if name not in teams: teams[name] = {"games": int(entry.get('GM', 0))}
            if key == "scoring_offense": teams[name]['pts'] = float(entry.get('PTS', 0))
            elif key == "scoring_defense": teams[name]['opp_pts'] = float(entry.get('OPP PTS', 0))
            elif key == "fg_pct": teams[name]['fga'] = float(entry.get('FGA', 0))
            elif key == "ft_pct": teams[name]['fta'] = float(entry.get('FTA', 0))
            elif key == "turnover_margin": teams[name]['to'] = float(entry.get('TO', 0))

    valid_teams = {}
    all_tempo, all_off_eff = [], []
    for name, stats in teams.items():
        if all(k in stats for k in ['fga', 'pts', 'opp_pts']) and stats['games'] > 0:
            # Stats are already "clean" averages, just using simple baseline
            poss = 0.96 * (stats['fga'] + (0.44 * stats.get('fta', 0)) + stats.get('to', 0))
            stats['tempo'] = poss / stats['games']
            stats['off_eff'] = (stats['pts'] / poss) * 100
            stats['def_eff'] = (stats['opp_pts'] / poss) * 100
            stats['conf'] = school_to_conf.get(name, "Other")
            
            all_tempo.append(stats['tempo'])
            all_off_eff.append(stats['off_eff'])
            valid_teams[name] = stats
            
    return valid_teams, sum(all_tempo)/len(all_tempo), sum(all_off_eff)/len(all_off_eff)

def predict_pessimistic(away_raw, home_raw, metrics, league_avgs):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    avg_tempo, avg_eff = league_avgs
    
    # 1. Tempo Drag Adjustment (The slower team wins)
    slow_tempo = min(tA['tempo'], tH['tempo'])
    fast_tempo = max(tA['tempo'], tH['tempo'])
    # Weighted average favors the slow team
    proj_tempo = (slow_tempo * TEMPO_DRAG) + (fast_tempo * (1 - TEMPO_DRAG))
    
    # 2. Road Penalty
    effA_raw = (tA['off_eff'] * tH['def_eff']) / 100
    effA = effA_raw * ROAD_PENALTY # Harsh penalty for visitors
    
    effH = (tH['off_eff'] * tA['def_eff']) / 100
    
    # 3. Mid-Major Cap
    # If a Mid-Major plays a Power Conference team, cap their efficiency
    if tA['conf'] not in POWER_CONFS and tH['conf'] in POWER_CONFS:
        effA = min(effA, 102) # Cap offensive output
    if tH['conf'] not in POWER_CONFS and tA['conf'] in POWER_CONFS:
        effH = min(effH, 105) # Caps even with Home Court
        
    scoreA = (effA * proj_tempo) / 100
    scoreH = (effH * proj_tempo) / 100
    
    return {
        "away": away_raw, "home": home_raw,
        "scoreA": round(scoreA, 1), "scoreH": round(scoreH, 1),
        "total": round(scoreA + scoreH, 1),
        "notes": f"Away Penalty: {(1-ROAD_PENALTY)*100:.0f}% | Tempo Drag: {proj_tempo:.1f}"
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    standings_data = load_json(STANDINGS_FILE)
    if not stats_data or not standings_data: return
    
    metrics, avg_tempo, avg_eff = get_pessimistic_metrics(stats_data, standings_data)
    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Conservative Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Proj Score':<15} | {'Total':<10}")
    print("-" * 75)
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away = game['away']['names']['short']
        home = game['home']['names']['short']
        
        res = predict_pessimistic(away, home, metrics, (avg_tempo, avg_eff))
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            score_str = f"{res['scoreA']} - {res['scoreH']}"
            print(f"{match_str:<40} | {score_str:<15} | {res['total']:<10}")
            print(f"  > Log: {res['notes']}")

if __name__ == "__main__":
    main()
