import argparse
import datetime
import time
import csv
import sys
import os
import statsapi

import run_daily_f5
from run_daily_f5 import get_today_games, get_pitcher_projected_ip
from fetch_lineups import get_lineup_for_game, get_pitcher_hand
from historical_weather import get_historical_weather
from grade_f5 import grade_matchup
from monte_carlo_f5 import run_monte_carlo_f5
from park_factors import get_park_factor

# Historical Point-in-time Fetchers
from historical_fetcher import (
    get_historical_pitcher_fip,
    get_historical_team_wrc,
    get_historical_team_bullpen_fip,
    get_historical_pitcher_avg_ip,
)
from historical_umpire import get_historical_umpire_profile

_umpire_cache = {}

def get_historical_umpire_for_game(game_id):
    """Fetches the actual home plate umpire for a historical game. Cached per game_id."""
    if game_id in _umpire_cache:
        return _umpire_cache[game_id]
    try:
        box = statsapi.get('game', {'gamePk': game_id})
        officials = box.get('liveData', {}).get('boxscore', {}).get('officials', [])
        for official in officials:
            if official.get('officialType') == 'Home Plate':
                name = official.get('official', {}).get('fullName', '')
                _umpire_cache[game_id] = name
                return name
        _umpire_cache[game_id] = None
        return None
    except Exception:
        _umpire_cache[game_id] = None
        return None

# Monkey-Patch requests.get with our Retry Session to survive MLB rate-limiting
import requests
from historical_fetcher import _session
requests.get = _session.get

# Monkey-Patch the live FIP fetcher so it returns a static 4.25 and avoids 30 API calls
run_daily_f5._fetch_live_league_fip = lambda *args, **kwargs: 4.25

def get_advice(line, td_total, under_prob, td_only=False):
    td_gap = line - td_total
    td_signal = 'UNDER' if td_gap > 0 else 'OVER'

    if td_only:
        # Grade purely on Top-Down vs the line, no confidence tiers
        return td_signal, 'TD-ONLY'

    if under_prob >= 0.52:
        mc_signal = 'UNDER'
    elif under_prob <= 0.48:
        mc_signal = 'OVER'
    else:
        mc_signal = 'NEUTRAL'

    if td_signal == mc_signal:
        mc_strong = under_prob >= 0.58 or under_prob <= 0.42
        confidence = 'HIGH' if (mc_strong and td_strong) else 'MODERATE'
        return mc_signal, confidence
    return 'SKIP', 'LOW'

def get_actual_f5_score(game_id):
    """Fetches the actual runs scored in the first 5 innings."""
    try:
        box = statsapi.get('game', {'gamePk': game_id})
        innings = box.get('liveData', {}).get('linescore', {}).get('innings', [])
        
        # Game was rained out or didn't reach 5 innings
        if len(innings) < 5:
            return None
            
        away_runs = sum([inning.get('away', {}).get('runs', 0) for inning in innings[:5]])
        home_runs = sum([inning.get('home', {}).get('runs', 0) for inning in innings[:5]])
        return away_runs + home_runs
    except Exception:
        return None

def run_backtest(start_date_str, end_date_str, team_filter=None, td_only=False):
    start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    current_date = start_date
    delta = datetime.timedelta(days=1)
    
    results = []
    
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        print(f"\n=============================================")
        print(f" Backtesting Date: {date_str}")
        print(f"=============================================")
        
        games = get_today_games(sport_id=1, date_str=date_str)
        if not games:
            print("No games found.")
            current_date += delta
            continue
            
        for g in games:
            away = g['away_team']
            home = g['home_team']
            
            if team_filter and team_filter.lower() not in away.lower() and team_filter.lower() not in home.lower():
                continue
                
            print(f"\nProcessing: {away} @ {home}")
            
            # This is a backtest, so we only care about games that actually finished and have F5 scores.
            # In a real backtester, we'd query the MLB API for the actual boxscore of this game to find the F5 score.
            # For this MVP proof of concept, we just generate the predictions and the user can match it.
            
            gid = g['game_id']
            ap = g['away_pitcher']
            hp = g['home_pitcher']
            ap_id = g.get('away_pitcher_id')
            hp_id = g.get('home_pitcher_id')
            
            if ap in ('TBD', '', None) or hp in ('TBD', '', None):
                print("Skipping - TBD Pitchers")
                continue
                
            ap_fip = get_historical_pitcher_fip(ap, date_str)
            hp_fip = get_historical_pitcher_fip(hp, date_str)
            
            if ap_fip is None or hp_fip is None:
                print("Skipping - Missing point-in-time FIP")
                continue
                
            away_bp = get_historical_team_bullpen_fip(away, date_str)
            home_bp = get_historical_team_bullpen_fip(home, date_str)
            
            away_wrc = get_historical_team_wrc(away, date_str)
            home_wrc = get_historical_team_wrc(home, date_str)
            
            # Use rolling historical avg IP to avoid leaking current-season data
            ap_ip = get_historical_pitcher_avg_ip(ap, date_str)
            hp_ip = get_historical_pitcher_avg_ip(hp, date_str)
            
            ap_hand = get_pitcher_hand(ap, sport_id=1)
            hp_hand = get_pitcher_hand(hp, sport_id=1)
            
            pf = get_park_factor(g['venue_name'])
            
            # Use historical point-in-time weather from the boxscore
            weather = get_historical_weather(gid)
            if not weather:
                # Fallback to neutral if boxscore is missing weather
                weather = {'temp_multiplier': 1.0, 'wind_multiplier': 1.0, 'weather_multiplier': 1.0, 'temp_fatigue_scaler': 1.0}
            weather_mult = weather.get('weather_multiplier', 1.0)
            
            # Fetch the actual umpire who called this game
            ump_name = get_historical_umpire_for_game(gid)
            ump_profile = get_historical_umpire_profile(ump_name, date_str) if ump_name else None
            
            top_down = grade_matchup(
                away, ap_fip, away_bp, ap_ip, away_wrc,
                home, hp_fip, home_bp, hp_ip, home_wrc,
                park_factor=pf,
                weather_multiplier=weather_mult,
                away_pitcher_hand=ap_hand,
                home_pitcher_hand=hp_hand,
            )
            td_total = top_down['projected_f5_total']
            
            # 2. Monte Carlo Model (Skip if TD-only)
            if td_only:
                mc = {'under_4_5_prob': 0.0}
            else:
                lineups = get_lineup_for_game(gid)
                mc = run_monte_carlo_f5(
                    lineups['away'], lineups['home'],
                    ap_id, hp_id, ap_fip, hp_fip,
                    iterations=10000, park_factor=pf, weather_context=weather, sport_id=1,
                    away_pitcher_hand=ap_hand, home_pitcher_hand=hp_hand,
                    umpire_profile=ump_profile
                )
            
            # We assume a standard Vegas line of 4.5 for the backtest
            signal, conf = get_advice(4.5, td_total, mc['under_4_5_prob'], td_only=td_only)
            
            actual_runs = get_actual_f5_score(gid)
            grade = "PENDING"
            
            if actual_runs is not None and signal != 'SKIP':
                if signal == 'OVER':
                    grade = "WIN" if actual_runs > 4.5 else "LOSS"
                elif signal == 'UNDER':
                    grade = "WIN" if actual_runs < 4.5 else "LOSS"
                    
            print(f"  TD: {td_total} | MC Under 4.5 Prob: {mc['under_4_5_prob']:.2f}")
            print(f"  -> Signal: {signal} ({conf}) | Actual F5 Runs: {actual_runs} | Grade: {grade}")
            
            results.append({
                'Date': date_str,
                'Matchup': f"{away} @ {home}",
                'TD Total': td_total,
                'MC Under 4.5 Prob': mc['under_4_5_prob'],
                'Signal': signal,
                'Confidence': conf,
                'Actual Runs': actual_runs,
                'Grade': grade
            })
            
        current_date += delta
        
    print("\n\n=============================================")
    print(" BACKTEST COMPLETE: GRADING SUMMARY")
    print("=============================================")
    
    wins = sum(1 for r in results if r['Grade'] == 'WIN')
    losses = sum(1 for r in results if r['Grade'] == 'LOSS')
    skips = sum(1 for r in results if r['Signal'] == 'SKIP')
    high_wins = sum(1 for r in results if r['Grade'] == 'WIN' and r['Confidence'] == 'HIGH')
    high_losses = sum(1 for r in results if r['Grade'] == 'LOSS' and r['Confidence'] == 'HIGH')
    
    total_bets = wins + losses
    win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
    
    high_bets = high_wins + high_losses
    high_win_rate = (high_wins / high_bets * 100) if high_bets > 0 else 0
    
    print(f"Total Games Processed: {len(results)}")
    print(f"Total Bets Placed: {total_bets} (Skipped {skips})")
    print(f"Overall Record: {wins}-{losses} ({win_rate:.1f}%)")
    print(f"HIGH Confidence Record: {high_wins}-{high_losses} ({high_win_rate:.1f}%)")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument('--end-date', type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument('--team', type=str, default=None)
    parser.add_argument('--td-only', action='store_true', help="Bypass Monte Carlo and only grade based on Top-Down model")
    args = parser.parse_args()
    
    run_backtest(args.start_date, args.end_date, args.team, args.td_only)
