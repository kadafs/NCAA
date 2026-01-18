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
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

# Data Paths
TEAM_STATS_FILE = "data/nba_stats.json"
PLAYER_STATS_FILE = "data/nba_player_stats.json"
MATCHUP_FILE = "data/nba_matchups.json"
INJURY_FILE = "data/nba_injury_notes.json"

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
    
    # Factors for player adjustment
    # If game projected higher scoring than team avg, players get boost
    factorA = projA / (sA['adj_off'] * (sA['adj_t']/100)) # Simple multiplier
    factorH = projH / (sH['adj_off'] * (sH['adj_t']/100))
    
    # 3. Player Props
    # Map team name to tricode if needed (nba_api uses full names in stats usually)
    away_props = [p for p in p_stats if p['team'] == matchup.get('away_abbr', away_raw)]
    if not away_props: # Try by city
        cityA = matchup.get('away_city', '')
        away_props = [p for p in p_stats if cityA in p['name'] or p['team'] in away_raw]
    
    # For now, let's just filter p_stats if they match team
    # (Actually nba_stats.json uses full names, p_stats usually uses tricode)
    # We'll use a simple direct filter for this demo
    
    return {
        "matchup": f"{away_raw} @ {home_raw}",
        "score": f"{projA:.1f} - {projH:.1f}",
        "spread": f"{projH - projA:+.1f}",
        "total": f"{projA + projH:.1f}",
        "pace": pace,
        "teamA": teamA,
        "teamH": teamH
    }

def main():
    team_stats = load_json(TEAM_STATS_FILE)
    p_stats = load_json(PLAYER_STATS_FILE)
    matchups = load_json(MATCHUP_FILE)
    injuries = load_json(INJURY_FILE)
    
    if not team_stats or not matchups:
        print("Required NBA data missing. Run fetch scripts first.")
        return

    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    print(f"\n" + "="*80)
    print(f"TOTAL NBA ANALYSIS: {now.strftime('%Y-%m-%d')}")
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
            
            # Show Prop Projections for Stars (if we have p_stats)
            if p_stats:
                print("   Top Player Projections:")
                # Simple logic to find key players for this matchup
                # (This part needs robust team mapping for players, showing mockup logic)
                found = 0
                for p in p_stats:
                    # Very simple matching for demo
                    if p['team'] in res['teamA'] or p['team'] in res['teamH']:
                        # Adjust stats based on pace/matchup (simulated)
                        adj_pts = p['pts'] * 1.05 # Matchup boost
                        print(f"     {p['name']:20} | Proj Pts: {adj_pts:4.1f} | Reb: {p['reb']:3.1f} | Ast: {p['ast']:3.1f}")
                        found += 1
                        if found > 4: break

if __name__ == "__main__":
    main()
