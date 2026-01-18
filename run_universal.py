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
    parser.add_argument("--league", choices=["nba", "ncaa", "euro"], default="nba", help="League to model")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    args = parser.parse_args()

    # 1. Config paths
    config_map = {
        "nba": "configs/leagues/nba.json",
        "ncaa": "configs/leagues/ncaa.json",
        "euro": "configs/leagues/euro.json"
    }
    
    # 2. Refresh if needed
    if args.refresh:
        # We can implement a unified refresher later
        print(f"Refreshing {args.league.upper()} data...")
        # Placeholder for subprocess calls to fetchers

    # 3. Initialize Engines
    engine = UniversalBasketballEngine(config_map[args.league], mode=args.mode)
    prop_engine = UniversalPropEngine(mode=args.mode)
    bridge = UniversalDataBridge(args.league)
    
    # 4. Load Metadata (Injuries & Players)
    p_stats = []
    injuries = {}
    if args.league == "nba":
        from nba.v1_2.populate import load_json, NBA_INJURY_FILE
        p_stats = load_json("data/nba_player_stats.json")
        if args.mode == "full":
            injuries = load_json(NBA_INJURY_FILE)
            
    # 5. Header
    now = datetime.now(ET_TZ)
    print("\n" + "█"*80)
    print(f" UNIVERSAL BASKETBALL FRAMEWORK v1.4 | {args.league.upper()} | {args.mode.upper()}")
    print(f" Timestamp: {now.strftime('%Y-%m-%d %H:%M')} ET")
    print("█"*80)

    # 6. Run Projections
    daily_sheet = bridge.get_standardized_sheet()
    
    if not daily_sheet:
        print(f"No {args.league.upper()} games found today.")
        return

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
            
        # Props (NBA only for now)
        if args.league == "nba" and p_stats:
            print("   Top Player Projections (Universal Prop Engine):")
            # Reuse logic from run_ultimate
            # (Simplified for the refactor)
            from nba.v1_2.populate import NBA_TRICODES
            full_to_tricode = {v: k for k, v in NBA_TRICODES.items()}
            
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            # Simple scaling factor
            factor = res['final_model_total'] / 230.0 # Pivot proxy
            context = {"factor": factor, "vol_factor": 1.0}

            for team_tri, label in [(triA, 'A'), (triH, 'H')]:
                if not team_tri: continue
                players = [p for p in p_stats if p['team'] == team_tri]
                players.sort(key=lambda x: x['seasonal']['pts'], reverse=True)
                
                for p in players[:3]:
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    print(f"     [{label}] {p['name']:20} | Pts: {p_proj['proj_pts']:4.1f} | Reb: {p_proj['proj_reb']:4.1f} | Ast: {p_proj['proj_ast']:3.1f}")
            
    print("\n" + "█"*80)
    print("Execution Finished.")

if __name__ == "__main__":
    main()
