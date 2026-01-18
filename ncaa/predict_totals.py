import json
import os
import requests
import zoneinfo
from datetime import datetime

# Script 2: Over/Under Focused Model
# Features: Offensive Rebounding (Possession Resets), 3PT Regression,
# Late Game Fouling (Free Throw Trap), and Tempo Archetypes.

BASE_URLS = ["http://localhost:3005", "http://localhost:3000", "https://ncaa-api.henrygd.me"]
TEAM_STATS_FILE = "data/consolidated_stats.json"
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

def get_total_metrics(stats_data):
    teams = {}
    all_tempo, all_off_eff, all_def_eff = [], [], []
    
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
            all_def_eff.append(stats['def_eff'])
            valid_teams[name] = stats
            
    return valid_teams, sum(all_tempo)/len(all_tempo), sum(all_def_eff)/len(all_def_eff)

def predict_total(away_raw, home_raw, metrics, league_avgs, barttorvik_data=None):
    nameA = find_team(away_raw, metrics)
    nameH = find_team(home_raw, metrics)
    
    # BartTorvik Specific Lookup
    btA_name = find_barttorvik_team(away_raw, barttorvik_data) if barttorvik_data else None
    btH_name = find_barttorvik_team(home_raw, barttorvik_data) if barttorvik_data else None
    
    if not nameA or not nameH: return None
    
    tA, tH = metrics[nameA], metrics[nameH]
    btA = barttorvik_data.get(btA_name) if btA_name else None
    btH = barttorvik_data.get(btH_name) if btH_name else None
    
    avg_tempo, avg_def = league_avgs[0], league_avgs[1]
    
    # Use BartTorvik if available, else fallback
    tempoA = btA['adj_t'] if btA else tA['tempo']
    tempoH = btH['adj_t'] if btH else tH['tempo']
    
    offA = btA['adj_off'] if btA else tA['off_eff']
    defA = btA['adj_def'] if btA else tA['def_eff']
    
    offH = btH['adj_off'] if btH else tH['off_eff']
    defH = btH['adj_def'] if btH else tH['def_eff']
    
    # 1. Base Projection
    proj_tempo = (tempoA * tempoH) / avg_tempo
    effA = (offA * defH) / avg_def
    effH = (offH * defA) / avg_def
    
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
        "logic": f"Reb: +{reb_bonusA+reb_bonusH:.1f} | 3PT Reg: {regA+regH:.1f} | FT Trap: +{ft_trap:.1f}",
        "using_bt": btA is not None and btH is not None
    }

def main():
    stats_data = load_json(TEAM_STATS_FILE)
    if not stats_data: return
    
    metrics, avg_tempo, avg_eff = get_total_metrics(stats_data)
    
    bt_stats = load_json(BARTTORVIK_STATS_FILE)
    if bt_stats:
        print(f"Loaded {len(bt_stats)} teams from BartTorvik for advanced precision.")
        avg_tempo = sum(t['adj_t'] for t in bt_stats.values()) / len(bt_stats)
        avg_eff = sum(t['adj_def'] for t in bt_stats.values()) / len(bt_stats)
    
    injury_notes = load_json(INJURY_NOTES_FILE)
    if injury_notes:
        print(f"Loaded injury notes for {len(injury_notes)} teams.")

    
    # Use current date in ET
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n--- Totals Predictions for {now.strftime('%Y-%m-%d')} ---")
    
    board = fetch_scoreboard(now.year, now.month, now.day)
    if not board or 'games' not in board or not board['games']:
        print("No games found on scoreboard.")
        return

    print(f"{'Matchup':<40} | {'Base Total':<12} | {'Adj Total':<12} | {'Diff':<8}")
    print("-" * 85)
    
    game_notes = []
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game: continue
        
        away = game['away']['names']['short']
        home = game['home']['names']['short']
        
        res = predict_total(away, home, metrics, (avg_tempo, avg_eff), bt_stats)
        if res:
            match_str = f"{res['away']} @ {res['home']}"
            if res.get('using_bt'):
                match_str += " *"
            print(f"{match_str:<40} | {res['base_total']:<12} | {res['adj_total']:<12} | {res['diff']:<8}")
            print(f"  > Log: {res['logic']}")

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
