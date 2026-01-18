import json
import os
import zoneinfo
from datetime import datetime
import sys

# Set encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES, NBA_TRICODES

# Data Paths (Absolute)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
TEAM_STATS_FILE = os.path.join(ROOT_DIR, "data", "nba_stats.json")
PLAYER_STATS_FILE = os.path.join(ROOT_DIR, "data", "nba_player_stats.json")
MATCHUP_FILE = os.path.join(ROOT_DIR, "data", "nba_matchups.json")
INJURY_FILE = os.path.join(ROOT_DIR, "data", "nba_injury_notes.json")

def load_json(path):
    if not os.path.exists(path): return None
    with open(path, "r") as f: return json.load(f)

def predict_game_with_props(matchup, team_stats, p_stats, injuries):
    away_raw = matchup['away']
    home_raw = matchup['home']
    
    # 1. Team Names
    teamA = find_team_in_dict(away_raw, team_stats)
    teamH = find_team_in_dict(home_raw, team_stats)
    if not teamA or not teamH: return None
    
    sA, sH = team_stats[teamA], team_stats[teamH]
    
    # 2. Score Projection
    pace = (sA['adj_t'] + sH['adj_t']) / 2
    effA = (sA['adj_off'] + sH['adj_def']) / 2
    effH = (sH['adj_off'] + sA['adj_def']) / 2
    
    projA = (pace / 100) * effA
    projH = (pace / 100) * effH + 2.5 # Home court
    
    # 3. Dynamic Factors for Props
    # scoring_factor: ratio of projected score vs team's season average score
    avg_ptsA = sA['adj_off'] * (sA['adj_t'] / 100)
    avg_ptsH = sH['adj_off'] * (sH['adj_t'] / 100)
    
    factorA = projA / avg_ptsA if avg_ptsA > 0 else 1.0
    factorH = projH / avg_ptsH if avg_ptsH > 0 else 1.0
    
    # volume_factor: for Rebounds/Possessions
    volA = pace / sA['adj_t'] if sA['adj_t'] > 0 else 1.0
    volH = pace / sH['adj_t'] if sH['adj_t'] > 0 else 1.0
    
    return {
        "matchup": f"{away_raw} @ {home_raw}",
        "score": f"{projA:.1f} - {projH:.1f}",
        "spread": f"{projH - projA:+.1f}",
        "total": f"{projA + projH:.1f}",
        "pace": pace,
        "teamA": teamA,
        "teamH": teamH,
        "factorA": factorA, "factorH": factorH,
        "volA": volA, "volH": volH
    }

def main():
    team_stats = load_json(TEAM_STATS_FILE)
    p_stats = load_json(PLAYER_STATS_FILE)
    matchups = load_json(MATCHUP_FILE)
    injuries = load_json(INJURY_FILE)
    
    if not team_stats or not matchups:
        print("Required NBA data missing. Run fetch scripts first.")
        return

    # Create mapping from full name to tricode for p_stats filter
    full_to_tricode = {v: k for k, v in NBA_TRICODES.items()}

    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n" + "="*80)
    print(f"TOTAL NBA ANALYSIS & PROJECTIONS: {now.strftime('%Y-%m-%d')}")
    print("="*80)
    
    for m in matchups:
        res = predict_game_with_props(m, team_stats, p_stats, injuries)
        if res:
            print(f"\n- MATCHUP: {res['matchup']}")
            print(f"   Score: {res['score']} | Total: {res['total']} | Spread: {res['spread']}")
            
            # Show Injuries
            away_inj = injuries.get(res['teamA'], [])
            home_inj = injuries.get(res['teamH'], [])
            if away_inj or home_inj:
                print("   Status:")
                for i in away_inj: print(f"     [A] {i['player']} ({i['status']}): {i['note'][:60]}...")
                for i in home_inj: print(f"     [H] {i['player']} ({i['status']}): {i['note'][:60]}...")
            
            # Show Prop Projections
            if p_stats:
                triA = full_to_tricode.get(res['teamA'])
                triH = full_to_tricode.get(res['teamH'])
                
                print("   Top Player Projections (Refined Matchup Scaling):")
                for team_tri, factor, vol, label in [(triA, res['factorA'], res['volA'], 'A'), (triH, res['factorH'], res['volH'], 'H')]:
                    if not team_tri: continue
                    team_players = [p for p in p_stats if p['team'] == team_tri]
                    # Sort by PPG to show stars
                    team_players.sort(key=lambda x: x.get('seasonal', {}).get('pts', 0), reverse=True)
                    
                    for p in team_players[:4]: # Top 4 players
                        # Use the 'seasonal' key for baseline
                        s = p.get('seasonal', {})
                        p_pts = s.get('pts', 0) * factor
                        p_ast = s.get('ast', 0) * factor
                        p_reb = s.get('reb', 0) * vol
                        
                        # Diff indicators for better insight
                        curr_pts = s.get('pts', 0)
                        diff = p_pts - curr_pts
                        mark = "↑" if diff > 1.5 else "↓" if diff < -1.5 else ""
                        
                        print(f"     [{label}] {p['name']:20} | Proj Pts: {p_pts:4.1f} {mark:1} | Reb: {p_reb:4.1f} | Ast: {p_ast:3.1f}")

if __name__ == "__main__":
    main()
