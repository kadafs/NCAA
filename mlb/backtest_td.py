"""
backtest_td.py
==============
Backtests the Top-Down F5 model against actual historical game results.
Unlike the consensus backtest, this grades PURELY on the Top-Down
projected total against a specified line (default 4.5).

Usage:
    python mlb/backtest_td.py --date 06/06/2026
    python mlb/backtest_td.py --date 06/06/2026 --line 5.5
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import statsapi
import argparse

# Use V3 logic for MLB (V3 includes Weather and tuned math)
from consensus_f5_v3 import get_pitcher_fip, get_team_bullpen_fip, get_team_wrc_proxy, get_pitcher_projected_ip
from grade_f5 import grade_matchup
from run_daily_f5 import get_today_games
from park_factors import get_park_factor
from weather_f5 import get_weather_modifier

def get_actual_f5_score(game_id):
    """
    Fetches the live box score for a completed game and returns the
    actual total runs scored through exactly 5 innings.
    Returns (away_f5_runs, home_f5_runs) or None if data unavailable.
    """
    try:
        boxscore = statsapi.get('game', {'gamePk': game_id, 'hydrate': 'linescore'})
        linescore = boxscore.get('liveData', {}).get('linescore', {})
        innings = linescore.get('innings', [])
        
        if len(innings) < 5:
            return None  # Game not complete / data missing
        
        away_f5 = sum(inn.get('away', {}).get('runs', 0) for inn in innings[:5])
        home_f5 = sum(inn.get('home', {}).get('runs', 0) for inn in innings[:5])
        return away_f5, home_f5
    except Exception as e:
        return None

def run_backtest(date_str, sport_id=1, line=4.5):
    """
    Runs the full backtest for a given date using only the Top-Down model.
    """
    print(f"\n{'='*60}")
    print(f"  TOP-DOWN MODEL BACKTEST - {date_str} (Line: {line})")
    print(f"{'='*60}\n")
    
    games = get_today_games(sport_id, date_str=date_str)
    if not games:
        print(f"No games found for {date_str}")
        return
    
    results = []
    
    for game in games:
        away = game['away_team']
        home = game['home_team']
        ap = game['away_pitcher']
        hp = game['home_pitcher']
        gid = game['game_id']
        venue = game.get('venue_name', 'Unknown Venue')
        
        print(f"Projecting: {away} @ {home}...")
        
        try:
            # --- Model projections (V3 Top-Down Architecture) ---
            ap_fip = get_pitcher_fip(ap, sport_id=sport_id)
            hp_fip = get_pitcher_fip(hp, sport_id=sport_id)
            ap_ip  = get_pitcher_projected_ip(ap, sport_id=sport_id)
            hp_ip  = get_pitcher_projected_ip(hp, sport_id=sport_id)
            away_bp = get_team_bullpen_fip(away, sport_id=sport_id)
            home_bp = get_team_bullpen_fip(home, sport_id=sport_id)
            away_wrc = get_team_wrc_proxy(away, sport_id)
            home_wrc = get_team_wrc_proxy(home, sport_id)
            
            pf = get_park_factor(venue)
            weather_data = get_weather_modifier(venue)
            weather_mult = weather_data['multiplier'] if isinstance(weather_data, dict) else 1.0
            
            top_down = grade_matchup(
                away, ap_fip, away_bp, ap_ip, away_wrc,
                home, hp_fip, home_bp, hp_ip, home_wrc,
                park_factor=pf,
                weather_multiplier=weather_mult,
                away_pitcher_hand='R', # Top-down approximation uses R
                home_pitcher_hand='R'
            )
            td_total = top_down['projected_f5_total']
            
            # --- Grading Logic ---
            if td_total < line:
                td_bet = "UNDER"
            elif td_total > line:
                td_bet = "OVER"
            else:
                td_bet = "PUSH"
            
            # --- Actual result ---
            actual = get_actual_f5_score(gid)
            if actual is not None:
                actual_total = actual[0] + actual[1]
                if actual_total < line:
                    actual_result = "UNDER"
                elif actual_total > line:
                    actual_result = "OVER"
                else:
                    actual_result = "PUSH"
            else:
                actual_total = None
                actual_result = "N/A"
            
            results.append({
                'matchup': f"{away} @ {home}",
                'td_total': td_total,
                'td_bet': td_bet,
                'actual_total': actual_total,
                'actual_result': actual_result,
            })
            
        except Exception as e:
            print(f"  ⚠️  SKIPPED {away} @ {home}: {e}")
            continue
    
    # --- Print Scorecard ---
    print(f"\n{'='*60}")
    print(f"  TOP-DOWN SCORECARD - {date_str} (Line: {line})")
    print(f"{'='*60}")
    
    bets = [r for r in results if r['td_bet'] != "PUSH"]
    wins = [r for r in bets if r['td_bet'] == r['actual_result']]
    losses = [r for r in bets if r['actual_result'] not in ['N/A', 'PUSH'] and r['td_bet'] != r['actual_result']]
    pushes = [r for r in results if r['actual_result'] == "PUSH" or r['td_bet'] == "PUSH"]
    
    for r in results:
        actual_str = f"{r['actual_total']} runs ({r['actual_result']})" if r['actual_total'] is not None else "N/A"
        
        if r['actual_result'] == 'N/A':
            verdict = "[PENDING]"
        elif r['td_bet'] == "PUSH" or r['actual_result'] == "PUSH":
            verdict = "[PUSH] "
        elif r['td_bet'] == r['actual_result']:
            verdict = "[WIN]  "
        else:
            verdict = "[LOSS] "
            
        print(f"\n  {r['matchup']}")
        print(f"    TD Proj: {r['td_total']:.2f} -> Bet {r['td_bet']} {line}")
        print(f"    Actual : {actual_str}  |  {verdict}")
    
    print(f"\n{'='*60}")
    print(f"  SUMMARY (Line: {line})")
    print(f"{'='*60}")
    print(f"  Total Games:   {len(results)}")
    print(f"  Bets Placed:   {len(bets)}")
    print(f"  Wins:          {len(wins)}")
    print(f"  Losses:        {len(losses)}")
    print(f"  Pushes/Skip:   {len(pushes)}")
    if len(bets) > 0:
        graded = len(wins) + len(losses)
        win_pct = (len(wins) / graded * 100) if graded > 0 else 0
        print(f"  Win Rate:      {win_pct:.1f}%  ({len(wins)}/{graded} graded picks)")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backtest the Top-Down model against actual results')
    parser.add_argument('--date', type=str, required=True, help='Date in MM/DD/YYYY format (e.g. 06/06/2026)')
    parser.add_argument('--sportId', type=int, default=1, help='1=MLB, 11=AAA, etc.')
    parser.add_argument('--line', type=float, default=4.5, help='The F5 line to grade against (default: 4.5)')
    args = parser.parse_args()
    
    run_backtest(args.date, args.sportId, line=args.line)
