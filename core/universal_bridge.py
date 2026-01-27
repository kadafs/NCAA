# Universal Bridge v1.5
# Standardizes output from the Universal Basketball Framework for the Next.js API.
import os
import sys
import json
from datetime import datetime
import zoneinfo

# Root addition
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.basketball_engine import UniversalBasketballEngine
from core.prop_engine import UniversalPropEngine
from core.data_bridge import UniversalDataBridge

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def get_universal_predictions(league="nba", mode="safe"):
    config_map = {
        "nba": "configs/leagues/nba.json",
        "ncaa": "configs/leagues/ncaa.json",
        "euro": "configs/leagues/euro.json",
        "eurocup": "configs/leagues/eurocup.json",
        "nbl": "configs/leagues/nbl.json",
        "acb": "configs/leagues/acb.json"
    }
    
    if league not in config_map:
        return {"error": f"Invalid league: {league}"}

    # 1. Initialize Engines
    engine = UniversalBasketballEngine(config_map[league], mode=mode)
    prop_engine = UniversalPropEngine(mode=mode)
    bridge = UniversalDataBridge(league)
    
    # 2. Load Metadata (Injuries & Players)
    p_stats = []
    injuries = {}
    
    # Simplified metadata loading for the bridge
    if league == "nba":
        try:
            from nba.v1_2.populate import load_json, NBA_INJURY_FILE
            p_stats_raw = load_json("data/nba_player_stats.json")
            # Bridge flat stats
            for p in p_stats_raw:
                if 'seasonal' not in p:
                    p_stats.append({
                        **p,
                        "id": p.get('id'),
                        "league": "nba",
                        "seasonal": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)},
                        "recent": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)}
                    })
                else:
                    p.update({"league": "nba"})
                    p_stats.append(p)
            
            if mode == "full":
                injuries = load_json(NBA_INJURY_FILE)
        except Exception as e:
            print(f"Error loading NBA metadata: {e}")
    elif league == "ncaa":
        try:
            from ncaa.v1_2.populate import load_json, INJURY_FILE
            if mode == "full":
                injuries = load_json(INJURY_FILE)
        except Exception as e:
            print(f"Error loading NCAA metadata: {e}")
    elif league == "euro":
        try:
            from euro.v1_2.populate import load_json
            p_stats_raw = load_json("data/euro_player_stats.json")
            for p in p_stats_raw:
                # Bridge flat stats to seasonal/recent
                p_stats.append({
                    **p,
                    "id": p.get('id'),
                    "league": "euro",
                    "seasonal": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)},
                    "recent": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)}
                })
            # No centralized injury file for EuroLeague yet, but we'll check it anyway
            if mode == "full":
                injuries = load_json("data/euro_injury_notes.json")
        except Exception as e:
            print(f"Error loading EuroLeague metadata: {e}")
    elif league == "eurocup":
        try:
            from eurocup.v1_2.populate import load_json
            p_stats_raw = load_json("data/eurocup_player_stats.json")
            for p in p_stats_raw:
                p_stats.append({
                    **p,
                    "id": p.get('id'),
                    "league": "eurocup",
                    "seasonal": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)},
                    "recent": {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)}
                })
            if mode == "full":
                injuries = load_json("data/eurocup_injury_notes.json")
        except Exception as e:
            print(f"Error loading EuroCup metadata: {e}")
    elif league == "nbl":
        # NBL metadata stubs
        pass
    elif league == "acb":
        # ACB metadata stubs
        pass
            
    # 3. Fetch Data
    daily_sheet = bridge.get_standardized_sheet()
    if not daily_sheet:
        return {
            "league": league,
            "timestamp": datetime.now(ET_TZ).isoformat(),
            "games": []
        }

    # 4. Process Matchups
    processed_games = []
    for game in daily_sheet:
        away = game.get('team')
        home = game.get('opponent')
        
        # Injuries
        game_injuries = []
        if mode == "full":
            game_injuries.extend(injuries.get(away, []))
            game_injuries.extend(injuries.get(home, []))
            
        # Calculation
        res = engine.calculate_total(game, game_injuries)
        
        # Props
        player_props = []
        if league == "nba" and p_stats:
            from nba.v1_2.populate import NBA_TRICODES
            full_to_tricode = {v: k for k, v in NBA_TRICODES.items()}
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            # Simple scaling factor (consistent with run_universal.py)
            factor = res['final_model_total'] / 230.0
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: x['seasonal']['pts'], reverse=True)
                
                for p in players[:10]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    player_props.append({
                        "id": p.get('id'),
                        "name": p['name'],
                        "team_label": label,
                        "league": "nba",
                        "pts": round(p_proj['proj_pts'], 1),
                        "reb": round(p_proj['proj_reb'], 1),
                        "ast": round(p_proj['proj_ast'], 1),
                        "stl": round(p_proj.get('proj_stl', 0), 1),
                        "blk": round(p_proj.get('proj_blk', 0), 1),
                        "tov": round(p_proj.get('proj_tov', 0), 1),
                        "threes": round(p_proj.get('proj_3pm', 0), 1),
                        "fgm": round(p_proj.get('proj_fgm', 0), 1),
                        "fga": round(p_proj.get('proj_fga', 0), 1),
                        "ftm": round(p_proj.get('proj_ftm', 0), 1),
                        "fta": round(p_proj.get('proj_fta', 0), 1),
                        "trace": p_proj['trace']
                    })
        elif league == "euro" and p_stats:
            from utils.mapping import EURO_TRICODES
            full_to_tricode = {v: k for k, v in EURO_TRICODES.items()}
            # Note: Euro API often uses tricodes directly or full names
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            # Use placeholders if tricode mapping fails but we have codes in p_stats
            # We'll also try a direct check if away/home are already codes
            if not triA: triA = away if any(p['team'] == away for p in p_stats) else None
            if not triH: triH = home if any(p['team'] == home for p in p_stats) else None
            
            # Simple scaling factor for Euro
            factor = res['final_model_total'] / 160.0
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: x['seasonal']['pts'], reverse=True)
                
                for p in players[:10]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    player_props.append({
                        "id": p.get('id'),
                        "name": p['name'],
                        "team_label": label,
                        "league": "euro",
                        "pts": round(p_proj['proj_pts'], 1),
                        "reb": round(p_proj['proj_reb'], 1),
                        "ast": round(p_proj['proj_ast'], 1),
                        "stl": round(p_proj.get('proj_stl', 0), 1),
                        "blk": round(p_proj.get('proj_blk', 0), 1),
                        "tov": round(p_proj.get('proj_tov', 0), 1),
                        "threes": round(p_proj.get('proj_3pm', 0), 1),
                        "trace": p_proj['trace']
                    })
        elif league == "eurocup" and p_stats:
            from utils.mapping import EUROCUP_TRICODES
            full_to_tricode = {v: k for k, v in EUROCUP_TRICODES.items()}
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            if not triA: triA = away if any(p['team'] == away for p in p_stats) else None
            if not triH: triH = home if any(p['team'] == home for p in p_stats) else None
            
            # EuroCup scaling factor
            factor = res['final_model_total'] / 165.0
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: x['seasonal']['pts'], reverse=True)
                
                for p in players[:10]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    player_props.append({
                        "id": p.get('id'),
                        "name": p['name'],
                        "team_label": label,
                        "league": "eurocup",
                        "pts": round(p_proj['proj_pts'], 1),
                        "reb": round(p_proj['proj_reb'], 1),
                        "ast": round(p_proj['proj_ast'], 1),
                        "stl": round(p_proj.get('proj_stl', 0), 1),
                        "blk": round(p_proj.get('proj_blk', 0), 1),
                        "tov": round(p_proj.get('proj_tov', 0), 1),
                        "threes": round(p_proj.get('proj_3pm', 0), 1),
                        "trace": p_proj['trace']
                    })
        
        processed_games.append({
            "matchup": f"{away} @ {home}",
            "away": away,
            "home": home,
            "away_details": game.get('away_details'),
            "home_details": game.get('home_details'),
            "market_total": round(res['market_total'], 1),
            "model_total": round(res['final_model_total'], 1),
            "edge": round(res['edge'], 2),
            "decision": res['decision'],
            "mode": res['mode'],
            "trace": res['trace'],
            "props": player_props,
            "statsA": game.get('statsA', {}),
            "statsH": game.get('statsH', {}),
            "injuries": game_injuries
        })

    return {
        "league": league,
        "mode": mode,
        "timestamp": datetime.now(ET_TZ).isoformat(),
        "games": processed_games
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--league", default="nba")
    parser.add_argument("--mode", default="safe")
    args = parser.parse_args()
    
    result = get_universal_predictions(args.league, args.mode)
    print(json.dumps(result, indent=2))
