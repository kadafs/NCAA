"""
backtest_f5.py
==============
Backtests the consensus F5 model against actual historical game results.

Usage:
    python mlb/backtest_f5.py --date 06/06/2026
    python mlb/backtest_f5.py --date 06/06/2026 --sportId 1

How it works:
    1. Runs the consensus model on the given historical date (projections).
    2. Fetches actual game-by-game box score data from statsapi.
    3. Extracts the real F5 score (sum of runs in innings 1-5).
    4. Compares model picks vs actual results and prints a scorecard.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import statsapi
import datetime
import argparse

from run_daily_f5 import get_today_games, get_pitcher_fip, get_team_wrc_proxy
from grade_f5 import grade_matchup
from fetch_lineups import get_lineup_for_game
from monte_carlo_f5 import run_monte_carlo_f5
from park_factors import get_park_factor


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


def run_backtest(date_str, sport_id=1):
    """
    Runs the full backtest for a given date.
    """
    print(f"\n{'='*60}")
    print(f"  MLB F5 BACKTEST - {date_str}")
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
        pf = get_park_factor(venue)
        
        print(f"Projecting: {away} @ {home} (PF={pf})...")
        
        # --- Model projections ---
        ap_fip = get_pitcher_fip(ap)
        hp_fip = get_pitcher_fip(hp)
        away_wrc = get_team_wrc_proxy(away, sport_id)
        home_wrc = get_team_wrc_proxy(home, sport_id)
        
        top_down = grade_matchup(away, ap_fip, away_wrc, home, hp_fip, home_wrc, park_factor=pf)
        td_total = top_down['projected_f5_total']
        
        lineups = get_lineup_for_game(gid)
        mc = run_monte_carlo_f5(lineups['away'], lineups['home'], ap, hp, ap_fip, hp_fip,
                                iterations=2000, park_factor=pf)
        
        # Consensus signal at the 4.5 line (most common F5 line)
        td_signal = "UNDER" if td_total < 4.5 else "OVER"
        mc_u45 = mc['under_4_5_prob']
        mc_signal = "UNDER" if mc_u45 >= 0.52 else ("OVER" if mc_u45 <= 0.48 else "NEUTRAL")
        consensus = mc_signal if td_signal == mc_signal else "SKIP"
        
        # --- Actual result ---
        actual = get_actual_f5_score(gid)
        if actual is not None:
            actual_total = actual[0] + actual[1]
            actual_result = "UNDER" if actual_total < 4.5 else "OVER"
        else:
            actual_total = None
            actual_result = "N/A"
        
        results.append({
            'matchup': f"{away} @ {home}",
            'venue': venue,
            'pf': pf,
            'td_total': td_total,
            'mc_total': mc['mc_total_runs'],
            'consensus': consensus,
            'actual_total': actual_total,
            'actual_result': actual_result,
        })
    
    # --- Print Scorecard ---
    print(f"\n{'='*60}")
    print(f"  BACKTEST SCORECARD - {date_str} (Line: 4.5)")
    print(f"{'='*60}")
    
    bets = [r for r in results if r['consensus'] not in ['SKIP', 'NEUTRAL']]
    wins = [r for r in bets if r['consensus'] == r['actual_result']]
    losses = [r for r in bets if r['actual_result'] != 'N/A' and r['consensus'] != r['actual_result']]
    skipped = [r for r in results if r['consensus'] in ['SKIP', 'NEUTRAL']]
    
    for r in results:
        actual_str = f"{r['actual_total']} runs ({r['actual_result']})" if r['actual_total'] is not None else "N/A"
        
        if r['consensus'] in ['SKIP', 'NEUTRAL']:
            verdict = "[SKIP]"
        elif r['consensus'] == r['actual_result']:
            verdict = "[WIN] "
        elif r['actual_result'] == 'N/A':
            verdict = "[PENDING]"
        else:
            verdict = "[LOSS]"
        
        print(f"\n  {r['matchup']}")
        print(f"    Venue: {r['venue']} (PF={r['pf']})")
        print(f"    TD Proj: {r['td_total']} | MC Proj: {r['mc_total']} | Signal: {r['consensus']}")
        print(f"    Actual F5: {actual_str}  |  {verdict}")
    
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  Total Games:   {len(results)}")
    print(f"  Bets Placed:   {len(bets)}")
    print(f"  Skipped:       {len(skipped)}")
    print(f"  Wins:          {len(wins)}")
    print(f"  Losses:        {len(losses)}")
    if len(bets) > 0:
        graded = len(wins) + len(losses)
        win_pct = (len(wins) / graded * 100) if graded > 0 else 0
        print(f"  Win Rate:      {win_pct:.1f}%  ({len(wins)}/{graded} graded picks)")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Backtest the F5 consensus model against actual results')
    parser.add_argument('--date', type=str, required=True, help='Date in MM/DD/YYYY format (e.g. 06/06/2026)')
    parser.add_argument('--sportId', type=int, default=1, help='1=MLB, 11=AAA, etc.')
    args = parser.parse_args()
    
    run_backtest(args.date, args.sportId)
