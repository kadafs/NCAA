#!/usr/bin/env python3
"""
D2 PPG+PED Hybrid Totals Model (v1-D2)
Adapted from D1 PPG+PED Hybrid structure for Division 2 basketball.
"""

import json
import os
import sys
import csv
from datetime import datetime
import zoneinfo

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.append(ROOT_DIR)

from utils.ssl_adapter import get_robust_session
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

BASE_URLS = [
    "https://ncaa-api-w2ry.onrender.com",
    "http://localhost:3000"
]

def load_json(path):
    """Load JSON file."""
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def fetch_scoreboard(year, month, day, division="d2"):
    """Fetch D2 scoreboard."""
    session = get_robust_session(retries=2)
    for base in BASE_URLS:
        url = f"{base}/scoreboard/basketball-men/{division}/{year}/{month:02d}/{day:02d}"
        try:
            response = session.get(url, timeout=15)
            if response.status_code != 200:
                response = session.get(url, timeout=15, verify=False)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"DEBUG: Error fetching from {base}: {e}")
            continue
    return None

# ============================================================================
# STEP 1: Base Total Calculation
# ============================================================================

def calculate_base_total(stats_a, stats_b):
    """
    Base Total = (A_PPG + B_OPP_PPG + B_PPG + A_OPP_PPG) / 2
    """
    a_ppg = float(stats_a.get('PPG', 0))
    a_opp_ppg = float(stats_a.get('OPP PPG', 0))
    b_ppg = float(stats_b.get('PPG', 0))
    b_opp_ppg = float(stats_b.get('OPP PPG', 0))
    
    base = (a_ppg + b_opp_ppg + b_ppg + a_opp_ppg) / 2
    return base

# ============================================================================
# STEP 2: Pace Adjustment
# ============================================================================

def calculate_possessions(stats):
    """
    Possessions = FGA - OR + TO + (0.44 × FTA)
    OR estimated as 30% of total rebounds.
    """
    games = float(stats.get('GM', 1))
    fga = float(stats.get('FGA', 0)) / games
    fta = float(stats.get('FTA', 0)) / games
    to = float(stats.get('TO', 0)) / games
    total_reb = float(stats.get('REB', 0)) / games
    
    # Estimate OR as 30% of total rebounds
    or_estimate = total_reb * 0.30
    
    possessions = fga - or_estimate + to + (0.44 * fta)
    return possessions

def get_pace_adjustment(poss_a, poss_b, spread):
    """
    Pace tiers + spread context modifier.
    
    Pace (poss/g)  Classification  Adjustment
    >72            Fast            +3
    68-72          Above avg       +1
    64-67          Average         0
    60-63          Slow            -2
    <60            Very slow       -4
    
    Spread context:
    ≤3 pts         +2
    ≥10 pts        -3
    Otherwise      0
    """
    avg_pace = (poss_a + poss_b) / 2
    
    # Pace tier adjustment
    if avg_pace > 72:
        pace_adj = 3
    elif avg_pace >= 68:
        pace_adj = 1
    elif avg_pace >= 64:
        pace_adj = 0
    elif avg_pace >= 60:
        pace_adj = -2
    else:
        pace_adj = -4
    
    # Spread context modifier
    abs_spread = abs(spread)
    if abs_spread <= 3:
        pace_adj += 2
    elif abs_spread >= 10:
        pace_adj -= 3
    
    return pace_adj

# ============================================================================
# STEP 3: Efficiency Adjustment
# ============================================================================

def get_efficiency_adjustment(stats_a, stats_b, league_avg_ppg, league_avg_opp_ppg):
    """
    Offensive/defensive strength relative to league average.
    
    Team PPG vs league avg  Label           Adjustment
    +5 or more              Strong offense  +1
    -5 or worse             Weak offense    -1
    Otherwise               Average         0
    
    Opp PPG vs league avg   Label           Adjustment
    -5 or lower             Strong defense  -1
    +5 or higher            Weak defense    +1
    Otherwise               Average         0
    
    Combined efficiency rule:
    Both strong defenses    -4 to -6
    Strong def vs weak off  -3
    Both strong offenses    +3
    Average matchup         0
    """
    a_ppg = float(stats_a.get('PPG', 0))
    a_opp_ppg = float(stats_a.get('OPP PPG', 0))
    b_ppg = float(stats_b.get('PPG', 0))
    b_opp_ppg = float(stats_b.get('OPP PPG', 0))
    
    # Offensive strength
    a_off_strong = (a_ppg - league_avg_ppg) >= 5
    a_off_weak = (a_ppg - league_avg_ppg) <= -5
    b_off_strong = (b_ppg - league_avg_ppg) >= 5
    b_off_weak = (b_ppg - league_avg_ppg) <= -5
    
    # Defensive strength (lower OPP PPG = stronger defense)
    a_def_strong = (a_opp_ppg - league_avg_opp_ppg) <= -5
    a_def_weak = (a_opp_ppg - league_avg_opp_ppg) >= 5
    b_def_strong = (b_opp_ppg - league_avg_opp_ppg) <= -5
    b_def_weak = (b_opp_ppg - league_avg_opp_ppg) >= 5
    
    # Combined efficiency rules
    if a_def_strong and b_def_strong:
        return -5  # Both strong defenses
    elif (a_def_strong and b_off_weak) or (b_def_strong and a_off_weak):
        return -3  # Strong def vs weak off
    elif a_off_strong and b_off_strong:
        return 3   # Both strong offenses
    else:
        # Individual adjustments
        adj = 0
        if a_off_strong: adj += 1
        if a_off_weak: adj -= 1
        if b_off_strong: adj += 1
        if b_off_weak: adj -= 1
        if a_def_strong: adj -= 1
        if a_def_weak: adj += 1
        if b_def_strong: adj -= 1
        if b_def_weak: adj += 1
        return adj

# ============================================================================
# STEP 4: Turnover & Foul Modifiers
# ============================================================================

def get_turnover_foul_adjustment(stats_a, stats_b, league_avg_to, league_avg_pf=None):
    """
    Turnovers:
    Both high TO teams    -3
    One high TO team      -1
    Low TO matchup        +1
    
    Fouling (if PF available):
    Both foul-prone       +3
    One foul-prone        +1
    Disciplined teams     0
    """
    games_a = float(stats_a.get('GM', 1))
    games_b = float(stats_b.get('GM', 1))
    
    to_a = float(stats_a.get('TO', 0)) / games_a
    to_b = float(stats_b.get('TO', 0)) / games_b
    
    adj = 0
    
    # Turnover adjustment
    high_to_threshold = league_avg_to + 2
    low_to_threshold = league_avg_to - 2
    
    a_high_to = to_a >= high_to_threshold
    b_high_to = to_b >= high_to_threshold
    a_low_to = to_a <= low_to_threshold
    b_low_to = to_b <= low_to_threshold
    
    if a_high_to and b_high_to:
        adj -= 3
    elif a_high_to or b_high_to:
        adj -= 1
    elif a_low_to and b_low_to:
        adj += 1
    
    # Foul adjustment (if data available)
    # Note: PF not in consolidated stats, skip for now
    
    return adj

# ============================================================================
# STEP 5: Conference Bias
# ============================================================================

def get_conference_bias(conf_a, conf_b):
    """
    Conference style adjustment.
    
    Conference style  Adjustment
    Fast/high scoring +1 to +2
    Defensive/slow    -1 to -2
    Neutral           0
    
    For initial implementation, return 0 (neutral) for all conferences.
    Can be refined later with conference classifications.
    """
    # TODO: Add conference classification logic
    return 0

# ============================================================================
# STEP 6-9: Final Total, Edge, Tier Classification
# ============================================================================

def calculate_final_total(base, pace_adj, eff_adj, to_foul_adj, conf_bias, apply_safety=True):
    """
    Step 6: Final Model Total
    Step 9: Low-Total Safety Rule (disable boosts if < 138)
    """
    model_total = base + pace_adj + eff_adj + to_foul_adj + conf_bias
    
    # Low-total safety rule
    if apply_safety and model_total < 138:
        # Disable soft foul boost and volatility boosts
        # For now, just cap negative adjustments
        if to_foul_adj > 0:
            model_total -= to_foul_adj
    
    return model_total

def calculate_edge_and_tier(model_total, market_total):
    """
    Step 7: Edge = |Model Total - Market Line|
    Step 8: Bet Classification
    
    Edge    Tier
    ≥9.0    Tier A
    7.0-8.9 Tier B
    5.0-6.9 Lean
    <5.0    Pass
    """
    if market_total is None or market_total == "N/A":
        return None, "N/A"
    
    edge = abs(model_total - market_total)
    
    if edge >= 9.0:
        tier = "Tier A"
    elif edge >= 7.0:
        tier = "Tier B"
    elif edge >= 5.0:
        tier = "Lean"
    else:
        tier = "Pass"
    
    return edge, tier

# ============================================================================
# MAIN
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="D2 PPG+PED Hybrid Totals Model")
    parser.add_argument("--division", type=str, default="d2", help="NCAA Division (d2, d3)")
    args = parser.parse_args()
    
    division = args.division.lower()
    
    # Load D2 stats
    div_suffix = "" if division == "d1" else f"_{division}"
    stats_file = os.path.join(ROOT_DIR, "data", f"consolidated_stats{div_suffix}.json")
    stats_data = load_json(stats_file)
    
    if not stats_data:
        print(f"Stats data missing for {division} at {stats_file}")
        return
    
    # Calculate league averages
    ppg_list = []
    opp_ppg_list = []
    to_list = []
    
    for team, stats in stats_data.items():
        if 'PPG' in stats and 'OPP PPG' in stats:
            ppg_list.append(float(stats['PPG']))
            opp_ppg_list.append(float(stats['OPP PPG']))
        if 'TO' in stats and 'GM' in stats:
            to_list.append(float(stats['TO']) / float(stats['GM']))
    
    league_avg_ppg = sum(ppg_list) / len(ppg_list) if ppg_list else 75
    league_avg_opp_ppg = sum(opp_ppg_list) / len(opp_ppg_list) if opp_ppg_list else 75
    league_avg_to = sum(to_list) / len(to_list) if to_list else 12
    
    print(f"League Averages ({division.upper()}):")
    print(f"  PPG: {league_avg_ppg:.1f}")
    print(f"  OPP PPG: {league_avg_opp_ppg:.1f}")
    print(f"  TO/g: {league_avg_to:.1f}\n")
    
    # Fetch scoreboard
    now = datetime.now(zoneinfo.ZoneInfo("America/New_York"))
    board = fetch_scoreboard(now.year, now.month, now.day, division=division)
    
    if not board or 'games' not in board or not board['games']:
        print(f"No games found for {division.upper()} on {now.strftime('%Y-%m-%d')}")
        return
    
    # CSV output
    header = ["Matchup", "Model_Total", "Market_Total", "Edge", "Tier", 
              "Base", "Pace_Adj", "Eff_Adj", "TO_Foul_Adj", "Conf_Bias", 
              "Poss_A", "Poss_B", "Spread"]
    
    writer = csv.writer(sys.stdout)
    writer.writerow(header)
    
    # Process each game
    for game_wrapper in board['games']:
        game = game_wrapper.get('game')
        if not game:
            continue
        
        away_raw = game['away']['names']['short']
        home_raw = game['home']['names']['short']
        
        # Find teams in stats
        nameA = find_team_in_dict(away_raw, stats_data, BASKETBALL_ALIASES)
        nameH = find_team_in_dict(home_raw, stats_data, BASKETBALL_ALIASES)
        
        if not nameA or not nameH:
            continue
        
        stats_a = stats_data[nameA]
        stats_b = stats_data[nameH]
        
        # Step 1: Base Total
        base = calculate_base_total(stats_a, stats_b)
        
        # Step 2: Pace Adjustment
        poss_a = calculate_possessions(stats_a)
        poss_b = calculate_possessions(stats_b)
        
        # Estimate spread (simple: home team advantage ~3 pts)
        a_ppg = float(stats_a.get('PPG', 0))
        a_opp = float(stats_a.get('OPP PPG', 0))
        b_ppg = float(stats_b.get('PPG', 0))
        b_opp = float(stats_b.get('OPP PPG', 0))
        spread = ((b_ppg - b_opp) - (a_ppg - a_opp)) + 3  # +3 home advantage
        
        pace_adj = get_pace_adjustment(poss_a, poss_b, spread)
        
        # Step 3: Efficiency Adjustment
        eff_adj = get_efficiency_adjustment(stats_a, stats_b, league_avg_ppg, league_avg_opp_ppg)
        
        # Step 4: TO/Foul Adjustment
        to_foul_adj = get_turnover_foul_adjustment(stats_a, stats_b, league_avg_to)
        
        # Step 5: Conference Bias
        conf_a = stats_a.get('Conference', '')
        conf_b = stats_b.get('Conference', '')
        conf_bias = get_conference_bias(conf_a, conf_b)
        
        # Step 6: Final Total
        model_total = calculate_final_total(base, pace_adj, eff_adj, to_foul_adj, conf_bias)
        
        # Step 7-8: Edge and Tier (market totals not available for D2)
        market_total = "N/A"
        edge, tier = calculate_edge_and_tier(model_total, None)
        
        # Output
        matchup = f"{away_raw} @ {home_raw}"
        row = [
            matchup,
            round(model_total, 1),
            market_total,
            edge if edge else "N/A",
            tier,
            round(base, 1),
            pace_adj,
            eff_adj,
            to_foul_adj,
            conf_bias,
            round(poss_a, 1),
            round(poss_b, 1),
            round(spread, 1)
        ]
        
        writer.writerow(row)

if __name__ == "__main__":
    main()
