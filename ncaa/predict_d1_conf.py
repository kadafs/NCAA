#!/usr/bin/env python3
"""
D1 Conference-Only Prediction Model
Uses ONLY Barttorvik conference-only stats (conflimit=1) for pure conference-based analysis.
Does NOT mix with NCAA.com full-season data.
"""

import sys
import os
import json
from datetime import datetime
import zoneinfo

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(ROOT_DIR)

from core.basketball_engine import UniversalBasketballEngine
from utils.mapping import get_target_date, find_team_in_dict, BASKETBALL_ALIASES
from utils.ssl_adapter import get_robust_session

# Conference-only data file
BARTTORVIK_CONF_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats_conf.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "configs", "leagues", "ncaa.json")

def load_conf_stats():
    """Load conference-only Barttorvik stats."""
    if not os.path.exists(BARTTORVIK_CONF_FILE):
        print(f"ERROR: Conference-only stats not found at {BARTTORVIK_CONF_FILE}")
        print("Please run: python ncaa/fetch_barttorvik_conf.py")
        return None
    
    with open(BARTTORVIK_CONF_FILE, "r") as f:
        return json.load(f)

def fetch_scoreboard(year, month, day):
    """Fetch D1 scoreboard."""
    session = get_robust_session(retries=2)
    base_urls = [
        "https://ncaa-api-w2ry.onrender.com",
        "http://localhost:3000"
    ]
    
    for base in base_urls:
        url = f"{base}/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        try:
            response = session.get(url, timeout=15)
            if response.status_code != 200:
                response = session.get(url, timeout=15, verify=False)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            continue
    return None

def get_odds_for_game(away, home):
    """Get market total for a game."""
    from utils.odds_provider import get_odds, extract_total_for_matchup
    
    odds_data = get_odds("ncaa", provider='render')
    if odds_data:
        return extract_total_for_matchup(odds_data, away, home)
    return None

def build_game_data(away_name, home_name, away_stats, home_stats, market_total):
    """
    Build game data structure using ONLY Barttorvik conference stats.
    No mixing with NCAA.com data.
    """

    
    # Calculate pace and efficiency from Barttorvik stats
    pace_adj = (away_stats.get('adj_t', 68) + home_stats.get('adj_t', 68)) / 2
    eff_adj = (
        away_stats.get('adj_off', 105) + home_stats.get('adj_def', 105) +
        home_stats.get('adj_off', 105) + away_stats.get('adj_def', 105)
    ) / 4
    
    return {
        "team": away_name,
        "opponent": home_name,
        "pace_adjustment": pace_adj,
        "efficiency_adjustment": eff_adj,
        "market_total": market_total,
        "conf": away_stats.get('conf', 'DEFAULT'),
        "is_elite_offense": away_stats.get('adj_off', 0) > 118 or home_stats.get('adj_off', 0) > 118,
        "is_strong_defense": away_stats.get('adj_def', 0) < 95 or home_stats.get('adj_def', 0) < 95,
        "statsA": {
            "adj_off": away_stats.get('adj_off', 105),
            "adj_def": away_stats.get('adj_def', 105),
            "adj_t": away_stats.get('adj_t', 68),
            "efg": away_stats.get('efg', 50),
            "to": away_stats.get('to', 18),
            "or": away_stats.get('or', 28),
            "ftr": away_stats.get('ftr', 30),
            "four_factors": {
                "efg": away_stats.get('efg', 50),
                "tov": away_stats.get('to', 18),
                "orb": away_stats.get('or', 28),
                "ftr": away_stats.get('ftr', 30)
            }
        },
        "statsH": {
            "adj_off": home_stats.get('adj_off', 105),
            "adj_def": home_stats.get('adj_def', 105),
            "adj_t": home_stats.get('adj_t', 68),
            "efg": home_stats.get('efg', 50),
            "to": home_stats.get('to', 18),
            "or": home_stats.get('or', 28),
            "ftr": home_stats.get('ftr', 30),
            "four_factors": {
                "efg": home_stats.get('efg', 50),
                "tov": home_stats.get('to', 18),
                "orb": home_stats.get('or', 28),
                "ftr": home_stats.get('ftr', 30)
            }
        }
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="D1 Conference-Only Prediction Model")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    args = parser.parse_args()
    
    # Load conference-only stats
    conf_stats = load_conf_stats()
    if not conf_stats:
        return 1
    
    print(f"[OK] Loaded {len(conf_stats)} teams with conference-only stats")
    
    # Get target date
    target_date = get_target_date(args.date)
    
    # Fetch scoreboard
    board = fetch_scoreboard(target_date.year, target_date.month, target_date.day)
    
    if not board or 'games' not in board or not board['games']:
        print(f"No NCAA D1 games found for {target_date.strftime('%Y-%m-%d')}")
        return 0
    
    # Initialize engine
    engine = UniversalBasketballEngine(CONFIG_FILE, mode=args.mode)
    
    # Header
    print("\n" + "=" * 80)
    print(f" D1 CONFERENCE-ONLY MODEL | {args.mode.upper()} MODE")
    print(f" Data Source: Barttorvik Conference Stats ONLY (conflimit=1)")
    print(f" Target Date: {target_date.strftime('%Y-%m-%d')} ET")
    print("=" * 80)
    
    # Load injuries if in full mode
    injuries = {}
    if args.mode == "full":
        injury_file = os.path.join(ROOT_DIR, "data", "injury_notes.json")
        if os.path.exists(injury_file):
            with open(injury_file, "r") as f:
                injuries = json.load(f)
    
    # Process each game
    results = []
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game:
            continue
        
        away_raw = game['away']['names']['short']
        home_raw = game['home']['names']['short']
        
        # Find teams in conference stats
        away_name = find_team_in_dict(away_raw, conf_stats, BASKETBALL_ALIASES)
        home_name = find_team_in_dict(home_raw, conf_stats, BASKETBALL_ALIASES)
        
        if not away_name or not home_name:
            print(f"⚠ Skipping {away_raw} @ {home_raw} - not found in conference stats")
            continue
        
        away_stats = conf_stats[away_name]
        home_stats = conf_stats[home_name]
        
        # Get market total
        market_total = get_odds_for_game(away_raw, home_raw)
        if not market_total:
            market_total = 145.5  # Fallback
        
        # Build game data using ONLY Barttorvik conference stats
        game_data = build_game_data(away_name, home_name, away_stats, home_stats, market_total)
        
        # Get injuries for this game
        game_injuries = []
        if args.mode == "full":
            game_injuries.extend(injuries.get(away_name, []))
            game_injuries.extend(injuries.get(home_name, []))
        
        # Calculate prediction
        res = engine.calculate_total(game_data, game_injuries)
        
        print(f"\n[GAME] MATCHUP: {away_name} @ {home_name}")
        print(f"   Market: {res['market_total']:5.1f} | Model: {res['final_model_total']:5.1f} | Edge: {res['edge']:+5.2f} | [{res['mode']}] {res['decision']}")
        
        if args.trace:
            for t in res['trace']:
                print(f"     > {t}")
        
        # Display conference-only advanced metrics
        print("\n   Conference-Only Advanced Metrics:")
        
        def fmt_stat(label, s):
            return f"{label}: AdjT {s.get('adj_t', 0):4.1f} | OE: {s.get('adj_off', 0):5.1f} | DE: {s.get('adj_def', 0):4.1f} | eFG: {s.get('efg', 0):4.1f} | TO: {s.get('to', 0):4.1f} | OR: {s.get('or', 0):4.1f} | FTR: {s.get('ftr', 0):4.1f}"
        
        print(f"     [Away] {fmt_stat('Stats', away_stats)}")
        print(f"     [Home] {fmt_stat('Stats', home_stats)}")
        
        # Store result
        results.append({
            "matchup": f"{away_name} @ {home_name}",
            "away": away_name,
            "home": home_name,
            "market_total": res['market_total'],
            "model_total": res['final_model_total'],
            "edge": res['edge'],
            "decision": res['decision'],
            "mode": res['mode'],
            "confidence": res.get('confidence', 'N/A'),
            "timestamp": datetime.now(zoneinfo.ZoneInfo("America/New_York")).isoformat()
        })
    
    print("\n" + "=" * 80)
    print("Execution Finished.")
    print("=" * 80)
    
    # Save results for comparison
    output_file = os.path.join(ROOT_DIR, "data", "d1_conf_predictions.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[OK] Predictions saved to {output_file}")
    print(f"[OK] Used PURE conference-only Barttorvik stats (no NCAA.com mixing)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

