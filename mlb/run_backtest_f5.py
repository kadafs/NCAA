import argparse
import datetime
import time
import csv
import sys
import os

from run_daily_f5 import get_today_games, get_pitcher_projected_ip
from fetch_lineups import get_lineup_for_game, get_pitcher_hand
from weather_f5 import get_weather_modifier
from grade_f5 import grade_matchup
from monte_carlo_f5 import run_monte_carlo_f5
from park_factors import get_park_factor

# Historical Point-in-time Fetchers
from historical_fetcher import get_historical_pitcher_fip, get_historical_team_wrc, get_historical_team_bullpen_fip
from historical_umpire import get_historical_umpire_profile

def get_advice(line, td_total, under_prob):
    td_gap = line - td_total
    td_signal = 'UNDER' if td_gap > 0 else 'OVER'

    if under_prob >= 0.52:
        mc_signal = 'UNDER'
    elif under_prob <= 0.48:
        mc_signal = 'OVER'
    else:
        mc_signal = 'NEUTRAL'

    if td_signal == mc_signal:
        mc_strong = under_prob >= 0.58 or under_prob <= 0.42
        td_strong = abs(td_gap) >= 0.30
        conf = 'HIGH' if (mc_strong and td_strong) else 'MODERATE'
        return mc_signal, conf
    return 'SKIP', 'NONE'

def run_backtest(start_date_str, end_date_str, team_filter=None):
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
            
            ap_ip = get_pitcher_projected_ip(ap, sport_id=1)
            hp_ip = get_pitcher_projected_ip(hp, sport_id=1)
            
            ap_hand = get_pitcher_hand(ap, sport_id=1)
            hp_hand = get_pitcher_hand(hp, sport_id=1)
            
            pf = get_park_factor(g['venue_name'])
            weather = get_weather_modifier(g['venue_name'], away_abbr=away, home_abbr=home)
            weather_mult = weather.get('weather_multiplier', 1.0) if weather else 1.0
            
            ump_profile = get_historical_umpire_profile("Ben May", date_str) # MOCKED
            
            top_down = grade_matchup(
                away, ap_fip, away_bp, ap_ip, away_wrc,
                home, hp_fip, home_bp, hp_ip, home_wrc,
                park_factor=pf,
                weather_multiplier=weather_mult,
                away_pitcher_hand=ap_hand,
                home_pitcher_hand=hp_hand,
            )
            td_total = top_down['projected_f5_total']
            
            lineups = get_lineup_for_game(gid)
            mc = run_monte_carlo_f5(
                lineups['away'], lineups['home'],
                ap, hp, ap_fip, hp_fip,
                iterations=2000, park_factor=pf, weather_context=weather, sport_id=1,
                away_pitcher_hand=ap_hand, home_pitcher_hand=hp_hand,
                umpire_profile=ump_profile
            )
            
            # We assume a standard Vegas line of 4.5 for the backtest
            signal, conf = get_advice(4.5, td_total, mc['under_4_5_prob'])
            
            print(f"  TD: {td_total} | MC Under 4.5 Prob: {mc['under_4_5_prob']:.2f}")
            print(f"  -> Signal: {signal} ({conf})")
            
            results.append({
                'Date': date_str,
                'Matchup': f"{away} @ {home}",
                'TD Total': td_total,
                'MC Under 4.5 Prob': mc['under_4_5_prob'],
                'Signal': signal,
                'Confidence': conf
            })
            
        current_date += delta
        
    print("\n\nBacktest Complete.")
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start-date', type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument('--end-date', type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument('--team', type=str, default=None)
    args = parser.parse_args()
    
    run_backtest(args.start_date, args.end_date, args.team)
