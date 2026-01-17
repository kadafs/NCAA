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
BARTTORVIK_STATS_FILE = "data/barttorvik_stats.json"
INJURY_NOTES_FILE = "data/injury_notes.json"

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

def find_barttorvik_team(name, barttorvik_dict):
    if not name or not barttorvik_dict: return None
    if name in barttorvik_dict: return name
    
    def clean(n):
        return n.replace("St.", "State").replace(".", "").replace("(", "").replace(")", "").replace(" ", "").replace("'", "").lower()

    name_clean = clean(name)
    
    # 1. Try exact clean match
    for bt_name in barttorvik_dict:
        if clean(bt_name) == name_clean:
            return bt_name
            
    # 2. Common aliases
    aliases = {
        "uconn": "connecticut",
        "olemiss": "mississippi",
        "penn": "pennsylvania",
        "upenn": "pennsylvania",
        "miamifl": "miamifl",
        "miamioh": "miamioh",
        "stmarys": "saintmarys",
        "stmarysca": "saintmarys",
        "umkc": "kansascity",
        "fullerton": "calstfullerton",
        "longbeachstate": "calstlongbeach",
        "northridge": "calstnorthridge",
        "bakersfield": "calstbakersfield",
        "stthomasmn": "stthomas",
        "ulmonroe": "louisianamonroe",
        "louisiana": "louisianalafayette",
        "appstate": "appalachianstate",
        "westerncaro": "westerncarolina",
        "southerncaro": "southcarolina",
        "eastcaro": "eastcarolina",
        "coastalcaro": "coastalcarolina",
    }
    if name_clean in aliases:
        target = aliases[name_clean]
        for bt_name in barttorvik_dict:
            if clean(bt_name) == target:
                return bt_name
                
    # 3. Substring match
    for bt_name in barttorvik_dict:
        bt_clean = clean(bt_name)
        if name_clean in bt_clean or bt_clean in name_clean:
            return bt_name
            
    return None

def find_injury_team(name, injury_dict):
    if not name or not injury_dict: return None
    name_low = name.lower()
    for inj_team in injury_dict:
        inj_low = inj_team.lower()
        if name_low in inj_low or inj_low in name_low:
            return inj_team
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

def predict_pessimistic(away_raw, home_raw, metrics, league_avgs, barttorvik_data=None):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    
    # BartTorvik Specific Lookup
    btA_name = find_barttorvik_team(away_raw, barttorvik_data) if barttorvik_data else None
    btH_name = find_barttorvik_team(home_raw, barttorvik_data) if barttorvik_data else None
    
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    btA = barttorvik_data.get(btA_name) if btA_name else None
    btH = barttorvik_data.get(btH_name) if btH_name else None
    
    avg_tempo, avg_eff = league_avgs
    
    # Use BartTorvik if available
    tempoA = btA['adj_t'] if btA else tA['tempo']
    tempoH = btH['adj_t'] if btH else tH['tempo']
    
    offA = btA['adj_off'] if btA else tA['off_eff']
    defA = btA['adj_def'] if btA else tA['def_eff']
    
    offH = btH['adj_off'] if btH else tH['off_eff']
    defH = btH['adj_def'] if btH else tH['def_eff']
    
    # 1. Tempo Drag Adjustment (The slower team wins)
    slow_tempo = min(tempoA, tempoH)
    fast_tempo = max(tempoA, tempoH)
    # Weighted average favors the slow team
    proj_tempo = (slow_tempo * TEMPO_DRAG) + (fast_tempo * (1 - TEMPO_DRAG))
    
    # 2. Road Penalty
    effA_raw = (offA * defH) / 100
    effA = effA_raw * ROAD_PENALTY # Harsh penalty for visitors
    
    effH = (offH * defA) / 100
    
    # 3. Mid-Major Cap
    # If a Mid-Major plays a Power Conference team, cap their efficiency
    # We still use local conf info as BT data is efficiency focused
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
        "notes": f"Away Penalty: {(1-ROAD_PENALTY)*100:.0f}% | Tempo Drag: {proj_tempo:.1f}",
        "using_bt": btA is not None and btH is not None
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    standings_data = load_json(STANDINGS_FILE)
    if not stats_data or not standings_data: return
    
    metrics, avg_tempo, avg_eff = get_pessimistic_metrics(stats_data, standings_data)
    
    bt_stats = load_json(BARTTORVIK_STATS_FILE)
    if bt_stats:
        print(f"Loaded {len(bt_stats)} teams from BartTorvik for advanced precision.")
        avg_tempo = sum(t['adj_t'] for t in bt_stats.values()) / len(bt_stats)
        league_avgs = (avg_tempo, avg_eff)
    
    injury_notes = load_json(INJURY_NOTES_FILE)
    if injury_notes:
        print(f"Loaded injury notes for {len(injury_notes)} teams.")

    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Conservative Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Proj Score':<15} | {'Total':<10}")
    print("-" * 75)
    
    game_notes = []
    
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away = game['away']['names']['short']
        home = game['home']['names']['short']
        
        res = predict_pessimistic(away, home, metrics, (avg_tempo, avg_eff), bt_stats)
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            if res.get('using_bt'):
                match_str += " *"
            score_str = f"{res['scoreA']} - {res['scoreH']}"
            print(f"{match_str:<40} | {score_str:<15} | {res['total']:<10}")
            print(f"  > Log: {res['notes']}")

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
