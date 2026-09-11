import os
import json
import time
import datetime
import requests
from dotenv import load_dotenv
from core.xgot_engine import compute_match_xgot

load_dotenv()

API_KEY = os.environ.get("API_BASKETBALL_KEY")
GIST_ID = os.environ.get("LIVE_GIST_ID")
GITHUB_TOKEN = os.environ.get("GH_PAT")

HEADERS = {
    "x-apisports-key": API_KEY,
    "v": "3"
}

def safe_int(val):
    if val is None: return 0
    if isinstance(val, str):
        val = val.replace("%", "").strip()
        if not val: return 0
        try: return int(val)
        except: return 0
    return int(val)

def fetch_live_fixtures():
    url = "https://v3.football.api-sports.io/fixtures?live=all"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("response", [])

def fetch_statistics(fixture_id):
    url = f"https://v3.football.api-sports.io/fixtures/statistics?fixture={fixture_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("response", [])

def fetch_events(fixture_id):
    url = f"https://v3.football.api-sports.io/fixtures/events?fixture={fixture_id}"
    r = requests.get(url, headers=HEADERS)
    if r.status_code != 200:
        return []
    data = r.json()
    return data.get("response", [])

def parse_stats(stats_array):
    parsed = {
        "shots_on_goal": 0,
        "corners": 0,
        "possession": 50,
        "dangerous_attacks": 0,
        "fouls": 0,
        "yellow_cards": 0,
        "total_shots": 0,
        "saves": 0,
        "shots_insidebox": 0,
        "shots_outsidebox": 0
    }
    for item in stats_array:
        t = item["type"]
        v = safe_int(item["value"])
        if t == "Shots on Goal": parsed["shots_on_goal"] = v
        elif t == "Corner Kicks": parsed["corners"] = v
        elif t == "Ball Possession": parsed["possession"] = v
        elif t == "Dangerous Attacks": parsed["dangerous_attacks"] = v
        elif t == "Fouls": parsed["fouls"] = v
        elif t == "Yellow Cards": parsed["yellow_cards"] = v
        elif t == "Total Shots": parsed["total_shots"] = v
        elif t == "Goalkeeper Saves": parsed["saves"] = v
        elif t == "Shots insidebox": parsed["shots_insidebox"] = v
        elif t == "Shots outsidebox": parsed["shots_outsidebox"] = v
    return parsed

def get_predictions_dict(date_str):
    filepath = f"data/football/universal_predictions_{date_str}.json"
    if not os.path.exists(filepath):
        return {}
    
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    preds = {}
    if isinstance(data, dict):
        if "predictions" in data and isinstance(data["predictions"], list):
            for g in data["predictions"]:
                home = g.get("home_team")
                away = g.get("away_team")
                if home and away:
                    preds[f"{home} vs {away}"] = g
        else:
            # Format might be dict of leagues
            for lid, ldata in data.items():
                if isinstance(ldata, dict) and "games" in ldata:
                    for g in ldata["games"]:
                        home = g.get("home_team")
                        away = g.get("away_team")
                        if home and away:
                            preds[f"{home} vs {away}"] = g
    elif isinstance(data, list):
        for g in data:
            home = g.get("home_team")
            away = g.get("away_team")
            if home and away:
                preds[f"{home} vs {away}"] = g
                
    return preds

def update_gist(payload):
    if not GIST_ID or not GITHUB_TOKEN:
        print("Missing GIST_ID or GH_PAT, saving to local live_momentum.json only.")
        with open("live_momentum.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        return
        
    url = f"https://api.github.com/gists/{GIST_ID}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "files": {
            "live_momentum.json": {
                "content": json.dumps(payload, indent=2)
            }
        }
    }
    r = requests.patch(url, headers=headers, json=data)
    if r.status_code == 200:
        print("Gist updated successfully.")
    else:
        print("Failed to update gist:", r.status_code, r.text)

def run():
    print("Running Live In-Play Engine...")
    now = datetime.datetime.utcnow()
    preds = {}
    for delta in [-1, 0, 1]:
        d = now + datetime.timedelta(days=delta)
        day_preds = get_predictions_dict(d.strftime("%Y-%m-%d"))
        preds.update(day_preds)
    print(f"Loaded {len(preds)} tracked matches across yesterday/today/tomorrow.")
    
    live_fixtures = fetch_live_fixtures()
    print(f"Found {len(live_fixtures)} live fixtures.")
    
    live_data = []
    
    for f in live_fixtures:
        fix_id = f["fixture"]["id"]
        status = f["fixture"]["status"]["short"]
        elapsed = f["fixture"]["status"].get("elapsed", 0)
        
        home = f["teams"]["home"]["name"]
        away = f["teams"]["away"]["name"]
        match_str = f"{home} vs {away}"
        
        goals_h = f["goals"].get("home", 0) or 0
        goals_a = f["goals"].get("away", 0) or 0
        
        pred = preds.get(match_str)
        if not pred:
            continue # We only care about tracked matches
            
        # Fetch stats & events
        stats = fetch_statistics(fix_id)
        events = fetch_events(fix_id)
        
        h_id = f["teams"]["home"]["id"]
        a_id = f["teams"]["away"]["id"]
        
        h_stats = parse_stats([s for s in stats if s["team"]["id"] == h_id][0]["statistics"]) if stats and [s for s in stats if s["team"]["id"] == h_id] else parse_stats([])
        a_stats = parse_stats([s for s in stats if s["team"]["id"] == a_id][0]["statistics"]) if stats and [s for s in stats if s["team"]["id"] == a_id] else parse_stats([])
        
        h_reds = sum(1 for e in events if e["team"]["id"] == h_id and e["type"] == "Card" and "Red" in str(e.get("detail", "")))
        a_reds = sum(1 for e in events if e["team"]["id"] == a_id and e["type"] == "Card" and "Red" in str(e.get("detail", "")))
        
        # Calculate Pressure Index (PI)
        # PI = (ShotsOnGoal * 2) + Corners + max(0, Possession - 50) + (DangerousAttacks * 0.1)
        h_pi = round((h_stats["shots_on_goal"] * 2) + h_stats["corners"] + max(0, h_stats["possession"] - 50) + (h_stats["dangerous_attacks"] * 0.1), 1)
        a_pi = round((a_stats["shots_on_goal"] * 2) + a_stats["corners"] + max(0, a_stats["possession"] - 50) + (a_stats["dangerous_attacks"] * 0.1), 1)
        
        momentum_diff = h_pi - a_pi
        
        # Determine Triggers
        triggers = []
        
        # Compute real-time xGOT & Goalkeeper performance
        xgot_data = compute_match_xgot(
            home_stats=h_stats,
            away_stats=a_stats,
            goals_h=goals_h,
            goals_a=goals_a,
            pre_xg_home=pred.get("xg_home"),
            pre_xg_away=pred.get("xg_away")
        )
        h_xgot = xgot_data["xgot_home"]
        a_xgot = xgot_data["xgot_away"]

        # Underperformance Trigger (High pressure, 0 goals)
        if h_pi > 15 and goals_h == 0: triggers.append("HOME_GOAL_DUE")
        if a_pi > 15 and goals_a == 0: triggers.append("AWAY_GOAL_DUE")
        
        # xGOT Triggers
        if h_xgot >= 1.2 and goals_h == 0: triggers.append("HOME_KEEPER_UNDER_SIEGE")
        if a_xgot >= 1.2 and goals_a == 0: triggers.append("AWAY_KEEPER_UNDER_SIEGE")
        if xgot_data["home_gk_prevented"] >= 1.2: triggers.append("HOME_GK_HEROICS")
        if xgot_data["away_gk_prevented"] >= 1.2: triggers.append("AWAY_GK_HEROICS")
        
        # Pre-match favorite struggling trigger
        pre_home_win = pred.get("home_win_prob", 0)
        pre_away_win = pred.get("away_win_prob", 0)
        
        if pre_home_win > 60 and goals_h < goals_a and h_pi > a_pi:
            triggers.append("FAVORITE_DOWN_BUT_DOMINATING")
        if pre_away_win > 60 and goals_a < goals_h and a_pi > h_pi:
            triggers.append("FAVORITE_DOWN_BUT_DOMINATING")
            
        if h_reds > 0 or a_reds > 0:
            triggers.append("RED_CARD")
            
        # Extract recent events (last 5)
        recent_events = []
        for e in reversed(events): # newest first usually, or we reverse
            t = e.get("type", "")
            if t in ["Goal", "Card", "subst", "Var"]:
                recent_events.append({
                    "time": e.get("time", {}).get("elapsed", 0),
                    "type": t,
                    "detail": str(e.get("detail", "")),
                    "player": str(e.get("player", {}).get("name", "")),
                    "team": str(e.get("team", {}).get("name", ""))
                })
            if len(recent_events) >= 6:
                break
                
        live_data.append({
            "fixture_id": fix_id,
            "match": match_str,
            "status": status,
            "elapsed": elapsed,
            "score": f"{goals_h}-{goals_a}",
            "home_pi": h_pi,
            "away_pi": a_pi,
            "momentum_diff": momentum_diff,
            "home_xgot": h_xgot,
            "away_xgot": a_xgot,
            "total_xgot": xgot_data["xgot_total"],
            "home_gk_prevented": xgot_data["home_gk_prevented"],
            "away_gk_prevented": xgot_data["away_gk_prevented"],
            "xgot_insights": xgot_data["insights"],
            "red_cards": f"{h_reds}-{a_reds}",
            "pre_match_prediction": {
                "home_win": pre_home_win,
                "away_win": pre_away_win,
                "draw": pred.get("draw_prob", 0),
                "btts": pred.get("btts_prob", 0)
            },
            "triggers": triggers,
            "stats": {
                "home": h_stats,
                "away": a_stats
            },
            "recent_events": recent_events
        })
        
    # Sort by absolute momentum difference (most volatile games first)
    live_data.sort(key=lambda x: abs(x["momentum_diff"]), reverse=True)
    
    payload = {
        "updated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "active_games": len(live_data),
        "matches": live_data
    }
    
    update_gist(payload)
    print("Live Engine cycle complete.")

if __name__ == "__main__":
    run()
