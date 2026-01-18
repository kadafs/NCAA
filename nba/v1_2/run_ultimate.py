# NBA Ultimate Dashboard v1.2
import argparse
import json
import os
import sys
from datetime import datetime
import zoneinfo

# Set encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add root for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

try:
    from nba.v1_2.engine import NBATotalsEngine
    from nba.v1_2.prop_engine import NBAPropEngine
    from nba.v1_2.populate import get_nba_daily_input_sheet, load_json, NBA_INJURY_FILE, ROOT_DIR
except (ImportError, ValueError):
    from engine import NBATotalsEngine
    from prop_engine import NBAPropEngine
    from populate import get_nba_daily_input_sheet, load_json, NBA_INJURY_FILE, ROOT_DIR
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES, NBA_TRICODES

# Configuration
PLAYER_STATS_FILE = os.path.join(ROOT_DIR, "data", "nba_player_stats.json")
TEAM_STATS_FILE = os.path.join(ROOT_DIR, "data", "nba_stats.json")
ET_TZ = zoneinfo.ZoneInfo("America/New_York")

def main():
    parser = argparse.ArgumentParser(description="NBA Ultimate Dashboard v1.2")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--trace", action="store_true", help="Show full logic audit trace")
    args = parser.parse_args()

    # 1. Initialize Engines
    game_engine = NBATotalsEngine(mode=args.mode)
    prop_engine = NBAPropEngine(mode=args.mode)
    
    # 2. Load Data
    daily_sheet = get_nba_daily_input_sheet()
    p_stats_raw = load_json(PLAYER_STATS_FILE)
    team_stats = load_json(TEAM_STATS_FILE) # For metadata
    injuries = load_json(NBA_INJURY_FILE) if args.mode == "full" else {}
    
    # Bridge flat stats to v1.2 nested structure (seasonal/recent)
    p_stats = []
    for p in p_stats_raw:
        if 'seasonal' not in p:
            wrapped = {
                **p,
                "seasonal": {
                    "pts": p.get('pts', 0),
                    "reb": p.get('reb', 0),
                    "ast": p.get('ast', 0)
                },
                "recent": {
                    "pts": p.get('pts', 0),
                    "reb": p.get('reb', 0),
                    "ast": p.get('ast', 0)
                }
            }
            p_stats.append(wrapped)
        else:
            p_stats.append(p)
    
    full_to_tricode = {v: k for k, v in NBA_TRICODES.items()}

    # 3. Header
    now = datetime.now(ET_TZ)
    print("\n" + "█"*80)
    print(f" NBA ULTIMATE DASHBOARD v1.2 | {args.mode.upper()} MODE | {now.strftime('%Y-%m-%d %H:%M')} ET")
    print("█"*80)

    if not daily_sheet:
        print("No NBA matchups found or stats missing. Run refresh first.")
        return

    for game in daily_sheet:
        away = game['team']
        home = game['opponent']
        
        # A. Game Totals Prediction
        game_injuries = []
        if args.mode == "full":
            game_injuries.extend(injuries.get(away, []))
            game_injuries.extend(injuries.get(home, []))
        
        g_pred = game_engine.calculate_total(game, game_injuries)
        
        # Display Game Header
        print(f"\n🏀 MATCHUP: {away} @ {home}")
        print(f"   Market: {g_pred['market_total']:5.1f} | Model: {g_pred['final_model_total']:5.1f} | Edge: {g_pred['edge']:+5.2f} | [{g_pred['mode']}] {g_pred['decision']}")
        
        if args.trace:
            for t in g_pred['trace']: print(f"     > {t}")

        # B. Prop Projections (Usage Redistribution)
        if p_stats:
            # We need the prop-scaling factor from the game prediction
            # factor = proj_score / season_avg
            # We derive it from the engine's internal logic or recalculate
            
            # Simple scaling factor for this game
            sA = team_stats.get(away, {})
            sH = team_stats.get(home, {})
            
            # Prop Environment
            contextA = {
                "factor": g_pred['final_model_total'] / (sA.get('pts', 115) + sH.get('pts', 115)), # Simplified group factor
                "vol_factor": game.get('pace_adjustment', 100) / 100, # Pace scale
                "opp_allowed": sH.get('allowed', {})
            }
            contextH = {
                "factor": contextA['factor'],
                "vol_factor": contextA['vol_factor'],
                "opp_allowed": sA.get('allowed', {})
            }

            print("   Top Player Projections (v1.2 Redistribution):")
            triA = full_to_tricode.get(away)
            triH = full_to_tricode.get(home)
            
            for team_tri, context, label in [(triA, contextA, 'A'), (triH, contextH, 'H')]:
                if not team_tri: continue
                # Filter players for this team
                team_players = [p for p in p_stats if p['team'] == team_tri]
                # Sort by seasonal PPG to find stars
                team_players.sort(key=lambda x: x['seasonal']['pts'], reverse=True)
                
                for p in team_players[:4]: # Top 4 options
                    # Teammate injuries FOR THIS TEAM for usage vacuum
                    team_injs = injuries.get(away if label == 'A' else home, [])
                    
                    p_proj = prop_engine.project_player(p, context, team_injs)
                    
                    # Diff indicator
                    diff = p_proj['proj_pts'] - p['seasonal']['pts']
                    mark = "↑" if diff > 1.5 else "↓" if diff < -1.5 else " "
                    
                    print(f"     [{label}] {p['name']:20} | Pts: {p_proj['proj_pts']:4.1f} {mark} | Reb: {p_proj['proj_reb']:4.1f} | Ast: {p_proj['proj_ast']:3.1f}")
                    if args.trace:
                        for pt in p_proj['trace']: print(f"        - {pt}")

    print("\n" + "█"*80)
    print("Dashboard Complete. Use --trace for audit details.")

if __name__ == "__main__":
    main()
