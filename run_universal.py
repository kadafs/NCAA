# Unified Basketball Runner v1.4
import argparse
import sys
import os
import json
from datetime import datetime
import zoneinfo

# Root addition
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from core.basketball_engine import UniversalBasketballEngine
from core.prop_engine import UniversalPropEngine
from core.data_bridge import UniversalDataBridge

# Set encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def main():
    parser = argparse.ArgumentParser(description="Universal Basketball Framework v1.4")
    parser.add_argument("--league", choices=["nba", "ncaa", "euro", "eurocup", "nbl", "acb"], default="nba", help="League to model")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    args = parser.parse_args()

    # 1. Config paths & Target Date
    from utils.mapping import get_target_date
    target_date = get_target_date(args.date)
    
    config_map = {
        "nba": "configs/leagues/nba.json",
        "ncaa": "configs/leagues/ncaa.json",
        "euro": "configs/leagues/euro.json",
        "eurocup": "configs/leagues/eurocup.json",
        "nbl": "configs/leagues/nbl.json",
        "acb": "configs/leagues/acb.json"
    }
    
    # 2. Refresh if needed (Porting logic for multi-day)
    if args.refresh:
        print(f"Refreshing {args.league.upper()} data for {target_date.strftime('%Y-%m-%d')}...")
        if args.league == "nba":
            from nba.fetch_nba_schedule import fetch_nba_daily_schedule
            fetch_nba_daily_schedule(target_date)
        elif args.league == "euro":
            from euro.fetch_euro_schedule import fetch_euro_daily_schedule
            fetch_euro_daily_schedule(target_date)
        elif args.league == "eurocup":
            from eurocup.fetch_eurocup_schedule import fetch_eurocup_schedule
            fetch_eurocup_schedule(target_date)
        elif args.league == "nbl":
            from nbl.fetch_nbl_schedule import fetch_nbl_schedule
            from nbl.fetch_nbl_stats import fetch_nbl_stats
            fetch_nbl_schedule(target_date)
            fetch_nbl_stats()
        elif args.league == "acb":
            from acb.fetch_acb_schedule import fetch_acb_schedule
            from acb.fetch_acb_stats import fetch_acb_stats
            fetch_acb_schedule(target_date)
            fetch_acb_stats()
        # NCAA fetching is handled inside the bridge's population call for v1.2

    # 3. Initialize Engines
    engine = UniversalBasketballEngine(config_map[args.league], mode=args.mode)
    prop_engine = UniversalPropEngine(mode=args.mode)
    bridge = UniversalDataBridge(args.league)
    
    # 4. Initialize Data Bridge with date support
    if args.league == "ncaa":
        daily_sheet = bridge.get_standardized_sheet(date_obj=target_date)
    else:
        # Others use the matchups file written by refresh or existing file
        daily_sheet = bridge.get_standardized_sheet()
    
    if not daily_sheet:
        print(f"No {args.league.upper()} games found today.")
        return

    # 5. Header
    print("\n" + "█"*80)
    print(f" UNIVERSAL BASKETBALL FRAMEWORK v1.4 | {args.league.upper()} | {args.mode.upper()}")
    print(f" Target Date: {target_date.strftime('%Y-%m-%d')} ET")
    print("█"*80)

    # 4. Load Metadata (Injuries & Players) - RESTORED
    p_stats = []
    injuries = {}
    if args.league == "nba":
        from nba.v1_2.populate import load_json, NBA_INJURY_FILE
        p_stats = load_json("data/nba_player_stats.json")
        if args.mode == "full":
            injuries = load_json(NBA_INJURY_FILE)
    elif args.league == "eurocup":
        from eurocup.v1_2.populate import load_json
        p_stats = load_json("data/eurocup_player_stats.json")
        if args.mode == "full":
            injuries = load_json("data/eurocup_injury_notes.json")
    elif args.league == "euro":
        from euro.v1_2.populate import load_json
        p_stats = load_json("data/euro_player_stats.json")
        if args.mode == "full":
            injuries = load_json("data/euro_injury_notes.json")

    for game in daily_sheet:
        away = game.get('team')
        home = game.get('opponent')
        
        # Injuries for this game
        game_injuries = []
        if args.mode == "full":
            game_injuries.extend(injuries.get(away, []))
            game_injuries.extend(injuries.get(home, []))
            
        res = engine.calculate_total(game, game_injuries)
        
        print(f"\n🏀 MATCHUP: {away} @ {home}")
        print(f"   Market: {res['market_total']:5.1f} | Model: {res['final_model_total']:5.1f} | Edge: {res['edge']:+5.2f} | [{res['mode']}] {res['decision']}")
        
        if args.trace:
            for t in res['trace']: print(f"     > {t}")
            
        # Props
        if args.league in ["nba", "euro", "eurocup"] and p_stats:
            print(f"   Top Player Projections ({args.league.upper()}):")
            from utils.mapping import NBA_TRICODES, EURO_TRICODES, EUROCUP_TRICODES
            
            tricode_map = NBA_TRICODES if args.league == "nba" else EURO_TRICODES if args.league == "euro" else EUROCUP_TRICODES
            full_to_tricode = {v: k for k, v in tricode_map.items()}
            
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            # Use codes directly if mapping fails (e.g. Euro API already using codes)
            if not triA: triA = away if any(p['team'] == away for p in p_stats) else None
            if not triH: triH = home if any(p['team'] == home for p in p_stats) else None
            
            pivot_val = 230.0 if args.league == "nba" else 160.0 if args.league == "euro" else 165.0
            factor = res['final_model_total'] / pivot_val
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                # Handling seasonal vs flat stats
                def get_p_stats(p):
                    if 'seasonal' in p: return p['seasonal']
                    return {"pts": p.get('pts', 0), "reb": p.get('reb', 0), "ast": p.get('ast', 0)}

                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: get_p_stats(x)['pts'], reverse=True)
                
                for p in players[:3]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    # Wrap flat stats for prop engine if needed
                    if 'seasonal' not in p:
                        p = {**p, "seasonal": get_p_stats(p), "recent": get_p_stats(p)}
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    print(f"     [{label}] {p['name']:20} | Pts: {p_proj['proj_pts']:4.1f} | Reb: {p_proj['proj_reb']:4.1f} | Ast: {p_proj['proj_ast']:3.1f}")
            
    print("\n" + "█"*80)
    print("Execution Finished.")

if __name__ == "__main__":
    main()
