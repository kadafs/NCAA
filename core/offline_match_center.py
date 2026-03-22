import os
import json
import glob
from collections import defaultdict

def _find_league_file(league_id, league_name=None):
    """
    Identifies the correct localized JSON database for a league, 
    borrowing the robust slug-mapping logic from generate_advanced_metrics.py
    """
    map_file = "data/league_slug_map.json"
    target_slug = None
    
    if os.path.exists(map_file):
        with open(map_file, encoding="utf-8") as f:
            slug_map = json.load(f)
            # Reverse lookup the slug based on league_id
            for slug, l_id in slug_map.items():
                if int(l_id) == int(league_id):
                    target_slug = slug
                    break
                    
    # If we didn't find a slug, we check standard filenames directly
    files_to_check = []
    if target_slug:
        files_to_check.append(f"data/historical/proballers_{target_slug}.json")
        files_to_check.append(f"data/historical/flashscore_{target_slug}.json")
        files_to_check.append(f"data/historical/proballers_{target_slug.replace('_', '-')}.json")
        files_to_check.append(f"data/historical/flashscore_{target_slug.replace('_', '-')}.json")
        
    # Also check the raw API backup files
    files_to_check.append(f"data/historical/api_basketball_{league_id}.json")
    
    for f in files_to_check:
        if os.path.exists(f):
            return f
            
    return None

def _load_matches(file_path):
    try:
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "games" in data: return data["games"]
            if "matches" in data: return data["matches"]
            if "response" in data: return data["response"]
    except Exception:
        pass
    return []

def get_h2h(matches, team1, team2):
    """ Extract historical Head-to-Head from offline chronological arrays """
    h2h = []
    t1 = str(team1).lower()
    t2 = str(team2).lower()
    
    for m in matches:
        ht = str(m.get('home_team', '')).lower()
        at = str(m.get('away_team', '')).lower()
        
        match_t1_h = (t1 in ht) or (ht in t1 and len(ht) >= 4)
        match_t1_a = (t1 in at) or (at in t1 and len(at) >= 4)
        match_t2_h = (t2 in ht) or (ht in t2 and len(ht) >= 4)
        match_t2_a = (t2 in at) or (at in t2 and len(at) >= 4)
        
        if (match_t1_h and match_t2_a) or (match_t2_h and match_t1_a):
            h2h.append({
                "date": m.get("date", ""),
                "teams": {
                    "home": {"name": m.get("home_team")},
                    "away": {"name": m.get("away_team")}
                },
                "scores": {
                    "home": {"total": m.get("home_score")},
                    "away": {"total": m.get("away_score")}
                }
            })
            if len(h2h) >= 5:
                break
    return h2h

def get_recent_form(matches, team):
    """ Extract Recent Form for a specific team """
    recent = []
    t = str(team).lower()
    
    for m in matches:
        ht = str(m.get('home_team', '')).lower()
        at = str(m.get('away_team', '')).lower()
        
        match_h = (t in ht) or (ht in t and len(ht) >= 4)
        match_a = (t in at) or (at in t and len(at) >= 4)
        
        if match_h or match_a:
            is_home = match_h
            hs = m.get("home_score", 0)
            as_ = m.get("away_score", 0)
            
            h_winner = True if hs > as_ else False if hs < as_ else None
            a_winner = True if as_ > hs else False if as_ < hs else None
            
            recent.append({
                "date": m.get("date", ""),
                "teams": {
                    "home": {"name": m.get("home_team"), "winner": h_winner},
                    "away": {"name": m.get("away_team"), "winner": a_winner}
                },
                "scores": {
                    "home": {"total": hs},
                    "away": {"total": as_}
                }
            })
            if len(recent) >= 5:
                break
    return recent

def calculate_standings(matches):
    """ Calculate a generic standings table based on W-L tallies """
    standings = {}
    for m in matches:
        ht = m.get('home_team')
        at = m.get('away_team')
        hs = m.get('home_score', 0)
        as_ = m.get('away_score', 0)
        if not ht or not at: continue
        
        for t in [ht, at]:
            if t not in standings:
                standings[t] = {'w':0, 'l':0, 'pf':0, 'pa':0, 'form': []}
                
        if hs > as_:
            standings[ht]['w'] += 1
            standings[at]['l'] += 1
            if len(standings[ht]['form']) < 5: standings[ht]['form'].append('W')
            if len(standings[at]['form']) < 5: standings[at]['form'].append('L')
        elif as_ > hs:
            standings[at]['w'] += 1
            standings[ht]['l'] += 1
            if len(standings[ht]['form']) < 5: standings[ht]['form'].append('L')
            if len(standings[at]['form']) < 5: standings[at]['form'].append('W')
            
        standings[ht]['pf'] += hs
        standings[ht]['pa'] += as_
        standings[at]['pf'] += as_
        standings[at]['pa'] += hs
        
    s_list = []
    for team_name, st in standings.items():
        played = st['w'] + st['l']
        if played == 0: continue
        win_pct = st['w'] / played
        s_list.append({
            "team_name": team_name,
            "played": played,
            "w": st['w'],
            "l": st['l'],
            "win_pct": win_pct,
            "pf": st['pf'],
            "pa": st['pa'],
            "form": "".join(st['form'])
        })
    s_list.sort(key=lambda x: (x['win_pct'], x['w'], x['pf']-x['pa']), reverse=True)
    
    formatted = []
    for i, st in enumerate(s_list):
        formatted.append({
            "position": i + 1,
            "team": {"name": st["team_name"], "logo": ""},
            "games": {
                "played": st["played"],
                "win": {"total": st["w"], "percentage": f"{st['win_pct']:.3f}"},
                "lose": {"total": st["l"]}
            },
            "points": {
                "for": st["pf"],
                "against": st["pa"]
            },
            "form": st["form"]
        })
    return [formatted] if formatted else []

def compile_offline_match_center(league_id, league_name, home_team, away_team):
    """ Entry point for run_basketball_daily.py to execute the zero-cost build """
    file_path = _find_league_file(league_id, league_name)
    if not file_path:
        return {"h2h": [], "recentH": [], "recentA": [], "full_standings": [], "statsH": {}, "statsA": {}}
        
    matches = _load_matches(file_path)
    
    return {
        "h2h": get_h2h(matches, home_team, away_team),
        "recentH": get_recent_form(matches, home_team),
        "recentA": get_recent_form(matches, away_team),
        "full_standings": calculate_standings(matches),
        "statsH": {}, 
        "statsA": {}
    }
