#!/usr/bin/env python3
"""
D1 Hybrid Prediction Model
Combines 70% conference-only stats with 30% full-season stats for balanced predictions.
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
from utils.mapping import (
    get_target_date, 
    find_team_in_dict, 
    calculate_weighted_stats,
    BASKETBALL_ALIASES
)
from utils.ssl_adapter import get_robust_session

# Data files
BARTTORVIK_CONF_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats_conf.json")
BARTTORVIK_FULL_FILE = os.path.join(ROOT_DIR, "data", "barttorvik_stats.json")
CONFIG_FILE = os.path.join(ROOT_DIR, "configs", "leagues", "ncaa.json")

def load_json_file(filepath, description):
    """Load JSON file with error handling."""
    if not os.path.exists(filepath):
        print(f"WARNING: {description} not found at {filepath}")
        return None
    
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            print(f"[OK] Loaded {len(data)} teams from {description}")
            return data
    except Exception as e:
        print(f"ERROR loading {description}: {e}")
        return None

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
        except Exception:
            continue
    return None

def get_odds_for_game(away, home):
    """Get market total for a game."""
    from utils.odds_provider import get_odds, extract_total_for_matchup
    
    odds_data = get_odds("ncaa", provider='render')
    if odds_data:
        return extract_total_for_matchup(odds_data, away, home)
    return None

def build_hybrid_game_data(away_name, home_name, away_hybrid, home_hybrid, market_total):
    """
    Build game data structure using hybrid weighted stats.
    """
    # Calculate pace and efficiency from hybrid stats
    pace_adj = (away_hybrid.get('adj_t', 68) + home_hybrid.get('adj_t', 68)) / 2
    eff_adj = (
        away_hybrid.get('adj_off', 105) + home_hybrid.get('adj_def', 105) +
        home_hybrid.get('adj_off', 105) + away_hybrid.get('adj_def', 105)
    ) / 4
    
    return {
        "team": away_name,
        "opponent": home_name,
        "pace_adjustment": pace_adj,
        "efficiency_adjustment": eff_adj,
        "market_total": market_total,
        "conf": away_hybrid.get('conf', 'DEFAULT'),
        "is_elite_offense": away_hybrid.get('adj_off', 0) > 118 or home_hybrid.get('adj_off', 0) > 118,
        "is_strong_defense": away_hybrid.get('adj_def', 0) < 95 or home_hybrid.get('adj_def', 0) < 95,
        "statsA": {
            "adj_off": away_hybrid.get('adj_off', 105),
            "adj_def": away_hybrid.get('adj_def', 105),
            "adj_t": away_hybrid.get('adj_t', 68),
            "efg": away_hybrid.get('efg', 50),
            "to": away_hybrid.get('to', 18),
            "or": away_hybrid.get('or', 28),
            "ftr": away_hybrid.get('ftr', 30),
            "four_factors": {
                "efg": away_hybrid.get('efg', 50),
                "tov": away_hybrid.get('to', 18),
                "orb": away_hybrid.get('or', 28),
                "ftr": away_hybrid.get('ftr', 30)
            }
        },
        "statsH": {
            "adj_off": home_hybrid.get('adj_off', 105),
            "adj_def": home_hybrid.get('adj_def', 105),
            "adj_t": home_hybrid.get('adj_t', 68),
            "efg": home_hybrid.get('efg', 50),
            "to": home_hybrid.get('to', 18),
            "or": home_hybrid.get('or', 28),
            "ftr": home_hybrid.get('ftr', 30),
            "four_factors": {
                "efg": home_hybrid.get('efg', 50),
                "tov": home_hybrid.get('to', 18),
                "orb": home_hybrid.get('or', 28),
                "ftr": home_hybrid.get('ftr', 30)
            }
        }
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(description="D1 Hybrid Prediction Model (70% Conf + 30% Full)")
    parser.add_argument("--mode", choices=["safe", "full"], default="safe", help="Prediction mode")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--conf-weight", type=float, default=0.70, help="Conference stats weight (default: 0.70)")
    parser.add_argument("--full-weight", type=float, default=0.30, help="Full season stats weight (default: 0.30)")
    args = parser.parse_args()
    
    # Validate weights sum to 1.0
    if abs(args.conf_weight + args.full_weight - 1.0) > 0.001:
        print(f"ERROR: Weights must sum to 1.0 (got {args.conf_weight} + {args.full_weight} = {args.conf_weight + args.full_weight})")
        return 1
    
    # Load both data sources
    conf_stats = load_json_file(BARTTORVIK_CONF_FILE, "conference-only stats")
    full_stats = load_json_file(BARTTORVIK_FULL_FILE, "full-season stats")
    
    # Check if we have at least one data source
    if not conf_stats and not full_stats:
        print("ERROR: No data sources available. Please run data fetching scripts.")
        return 1
    
    # Determine data availability
    both_available = conf_stats is not None and full_stats is not None
    
    if not both_available:
        if conf_stats:
            print(f"[WARNING] Only conference stats available - using at 100%")
        else:
            print(f"[WARNING] Only full-season stats available - using at 100%")
    
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
    print(f" D1 HYBRID MODEL | {args.mode.upper()} MODE")
    print(f" Weighting: {args.conf_weight*100:.0f}% Conference + {args.full_weight*100:.0f}% Full Season")
    print(f" Data Sources: {'BOTH' if both_available else 'SINGLE'}")
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
        
        # Find teams in both data sources
        away_conf_name = find_team_in_dict(away_raw, conf_stats or {}, BASKETBALL_ALIASES)
        home_conf_name = find_team_in_dict(home_raw, conf_stats or {}, BASKETBALL_ALIASES)
        away_full_name = find_team_in_dict(away_raw, full_stats or {}, BASKETBALL_ALIASES)
        home_full_name = find_team_in_dict(home_raw, full_stats or {}, BASKETBALL_ALIASES)
        
        # Use whichever name was found (prefer conference)
        away_name = away_conf_name or away_full_name
        home_name = home_conf_name or home_full_name
        
        if not away_name or not home_name:
            print(f"⚠ Skipping {away_raw} @ {home_raw} - not found in data sources")
            continue
        
        # Get stats from both sources
        away_conf_stats = conf_stats.get(away_conf_name) if conf_stats and away_conf_name else None
        home_conf_stats = conf_stats.get(home_conf_name) if conf_stats and home_conf_name else None
        away_full_stats = full_stats.get(away_full_name) if full_stats and away_full_name else None
        home_full_stats = full_stats.get(home_full_name) if full_stats and home_full_name else None
        
        # Calculate weighted hybrid stats
        away_hybrid = calculate_weighted_stats(away_conf_stats, away_full_stats, args.conf_weight)
        home_hybrid = calculate_weighted_stats(home_conf_stats, home_full_stats, args.conf_weight)
        
        if not away_hybrid or not home_hybrid:
            print(f"⚠ Skipping {away_raw} @ {home_raw} - could not create hybrid stats")
            continue
        
        # Get market total
        market_total = get_odds_for_game(away_raw, home_raw)
        if not market_total:
            market_total = 145.5  # Fallback
        
        # Build game data using hybrid stats
        game_data = build_hybrid_game_data(away_name, home_name, away_hybrid, home_hybrid, market_total)
        
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
        
        # Display hybrid stats info
        print(f"\n   Hybrid Stats (Conf {args.conf_weight*100:.0f}% + Full {args.full_weight*100:.0f}%):")
        
        def fmt_hybrid(label, h):
            return f"{label}: AdjT {h.get('adj_t', 0):4.1f} | OE: {h.get('adj_off', 0):5.1f} | DE: {h.get('adj_def', 0):4.1f} | eFG: {h.get('efg', 0):4.1f}"
        
        print(f"     [Away] {fmt_hybrid('Hybrid', away_hybrid)}")
        print(f"     [Home] {fmt_hybrid('Hybrid', home_hybrid)}")
        
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
            "data_sources": {
                "conference_weight": args.conf_weight,
                "full_season_weight": args.full_weight,
                "both_available": both_available,
                "away_conf_available": away_conf_stats is not None,
                "away_full_available": away_full_stats is not None,
                "home_conf_available": home_conf_stats is not None,
                "home_full_available": home_full_stats is not None
            },
            "timestamp": datetime.now(zoneinfo.ZoneInfo("America/New_York")).isoformat()
        })
    
    print("\n" + "=" * 80)
    print("Execution Finished.")
    print("=" * 80)
    
    # Save results
    output_file = os.path.join(ROOT_DIR, "data", "d1_hybrid_predictions.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n[OK] Predictions saved to {output_file}")
    print(f"[OK] Used HYBRID model: {args.conf_weight*100:.0f}% conference + {args.full_weight*100:.0f}% full-season")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
