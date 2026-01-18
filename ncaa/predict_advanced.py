import json
import os
import requests
import zoneinfo
from datetime import datetime
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Script 1: General Accuracy Model
# Features: Home-Court Advantage, Conference-based Strength of Schedule (SoS),
# Weighted Efficiency and Four Factors.

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
# Base paths relative to Project Root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))

TEAM_STATS_FILE = os.path.join(ROOT_DIR, "data", "consolidated_stats.json")
STANDINGS_FILE = os.path.join(ROOT_DIR, "data", "standings.json")
BARTTORVIK_STATS_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")
INJURY_NOTES_FILE = os.path.join(ROOT_DIR, "data", "injury_notes.json")

# Conference Rankings Proxy (Higher = Stronger Conference)
# Based on historical/NET context
CONF_QUALITY = {
    "Big 12": 1.15, "SEC": 1.12, "Big Ten": 1.10, "ACC": 1.08, "Big East": 1.08,
    "Mountain West": 1.04, "Pac-12": 1.02, "American": 1.00, "WCC": 0.98,
    "Atlantic 10": 0.96, "Missouri Valley": 0.94, "Sun Belt": 0.92
}
DEFAULT_QUALITY = 0.85

HOME_ADVANTAGE = 3.5

def fetch_scoreboard(year, month, day):
    for base in BASE_URLS:
        url = f"{base}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return response.json()
        except Exception:
            continue
    return None

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

# Using shared find_team_in_dict from utils.mapping instead of local helpers

def find_injury_team(name, injury_dict):
    if not name or not injury_dict: return None
    name_low = name.lower()
    for inj_team in injury_dict:
        inj_low = inj_team.lower()
        if name_low in inj_low or inj_low in name_low:
            return inj_team
    return None

def get_team_metrics(stats_data, standings_data):
    # Map schools to conferences
    school_to_conf = {}
    if isinstance(standings_data, dict):
        data_list = standings_data.get('data', [])
        for conf_group in data_list:
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
            
    if not all_tempo:
        return {}, 0, 0, 0
            
    return valid_teams, sum(all_tempo)/len(all_tempo), sum(all_off_eff)/len(all_off_eff), sum(all_def_eff)/len(all_def_eff)

def predict_game(away_raw, home_raw, metrics, league_avgs, barttorvik_data=None):
    nameA = find_team_in_dict(away_raw, metrics, BASKETBALL_ALIASES)
    nameH = find_team_in_dict(home_raw, metrics, BASKETBALL_ALIASES)
    
    # BartTorvik Specific Lookup
    btA_name = find_team_in_dict(away_raw, barttorvik_data, BASKETBALL_ALIASES) if barttorvik_data else None
    btH_name = find_team_in_dict(home_raw, barttorvik_data, BASKETBALL_ALIASES) if barttorvik_data else None
    
    # We need metrics for basic info, but can prefer BartTorvik for calculations
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    btA = barttorvik_data.get(btA_name) if btA_name else None
    btH = barttorvik_data.get(btH_name) if btH_name else None
    
    avg_tempo, avg_off, avg_def = league_avgs
    
    # 1. Use BartTorvik if available, else fallback
    tempoA = btA['adj_t'] if btA else tA['tempo']
    tempoH = btH['adj_t'] if btH else tH['tempo']
    
    offA = btA['adj_off'] if btA else tA['off_eff']
    defA = btA['adj_def'] if btA else tA['def_eff']
    
    offH = btH['adj_off'] if btH else tH['off_eff']
    defH = btH['adj_def'] if btH else tH['def_eff']
    
    # 2. Projections using Adjusted Metrics
    proj_tempo = (tempoA * tempoH) / avg_tempo
    
    # Away Team Offense vs Home Team Defense
    effA = (offA * defH) / avg_def
    # Home Team Offense vs Away Team Defense
    effH = (offH * defA) / avg_def
    
    scoreA = (effA * proj_tempo) / 100
    scoreH = ((effH * proj_tempo) / 100) + HOME_ADVANTAGE
    
    return {
        "away": away_raw, "home": home_raw,
        "scoreA": round(scoreA, 1), "scoreH": round(scoreH, 1),
        "total": round(scoreA + scoreH, 1),
        "spread": round(scoreH - scoreA, 1),
        "using_bt": btA is not None and btH is not None
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    standings_data = load_json(STANDINGS_FILE)
    if not stats_data: 
        print("Stats file missing.")
        return

    metrics, avg_tempo, avg_off, avg_def = get_team_metrics(stats_data, standings_data)
    
    # Load BartTorvik stats for better precision
    bt_stats = load_json(BARTTORVIK_STATS_FILE)
    if bt_stats:
        print(f"Loaded {len(bt_stats)} teams from BartTorvik for advanced precision.")
        # Calculate BartTorvik league averages for more consistent normalization
        avg_tempo = sum(t['adj_t'] for t in bt_stats.values()) / len(bt_stats)
        avg_off = sum(t['adj_off'] for t in bt_stats.values()) / len(bt_stats)
        avg_def = sum(t['adj_def'] for t in bt_stats.values()) / len(bt_stats)
        
    league_avgs = (avg_tempo, avg_off, avg_def)
    
    injury_notes = load_json(INJURY_NOTES_FILE)
    if injury_notes:
        print(f"Loaded injury notes for {len(injury_notes)} teams.")

    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Advanced Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Proj Score':<15} | {'Total':<10} | {'Spread':<10} | {'Conf (A/H)':<10} | {'eFG/TO/OR/FTR (A)'}")
    print("-" * 130)
    
    game_notes = []
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away = game['away']['names']['short']
        home = game['home']['names']['short']
        
        res = predict_game(away, home, metrics, league_avgs, bt_stats)
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            if res.get('using_bt'):
                match_str += " *"
            score_str = f"{res['scoreA']} - {res['scoreH']}"
            
            # Additional Meta Display
            btA_name = find_team_in_dict(away, bt_stats, BASKETBALL_ALIASES)
            btH_name = find_team_in_dict(home, bt_stats, BASKETBALL_ALIASES)
            btA = bt_stats.get(btA_name) if btA_name else None
            btH = bt_stats.get(btH_name) if btH_name else None
            
            conf_str = f"{btA['conf'] if (btA and 'conf' in btA) else 'N/A'}/{btH['conf'] if (btH and 'conf' in btH) else 'N/A'}"
            # Show Four Factors for Away team vs Home team defense
            stats_str = "N/A"
            if btA and btH and btA.get('efg'):
                stats_str = f"{btA['efg']:.1f}/{btA['to']:.1f}/{btA['or']:.1f}/{btA['ftr']:.1f}"

            print(f"{match_str:<40} | {score_str:<15} | {res['total']:<10} | {res['spread']:<10} | {conf_str:<10} | {stats_str}")

            # Injury Notes matching
            injA_name = find_injury_team(away, injury_notes)
            injH_name = find_injury_team(home, injury_notes)
            
            notes = []
            if injA_name and injury_notes[injA_name]:
                for item in injury_notes[injA_name]:
                    notes.append(f"  [A] {item['player']} ({item['status']}): {item['note']}")
            if injH_name and injury_notes[injH_name]:
                for item in injury_notes[injH_name]:
                    notes.append(f"  [H] {item['player']} ({item['status']}): {item['note']}")
            
            if notes:
                game_notes.append((match_str, notes))

    if game_notes:
        print("\n" + "="*50)
        print("SITUATIONAL NOTES (Injuries, Travel, etc.)")
        print("="*50)
        for matchup, notes in game_notes:
            print(f"\n{matchup}:")
            for n in notes:
                print(n)

if __name__ == "__main__":
    main()
