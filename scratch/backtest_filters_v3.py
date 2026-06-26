import os
import sys
import datetime

# Ensure mlb directory is in python path
sys.path.append(os.path.abspath('mlb'))

from run_daily_f5 import get_today_games, get_team_f5_form_factor, get_pitcher_fip, get_team_wrc_proxy, get_team_bullpen_fip, get_pitcher_projected_ip
from run_backtest_f5 import get_actual_f5_score, get_historical_pitcher_fip, get_historical_team_bullpen_fip, get_historical_team_wrc, get_historical_pitcher_avg_ip, get_historical_weather, get_historical_umpire_for_game, get_historical_umpire_profile
from park_factors import get_park_factor_details, get_park_factor
from grade_f5 import grade_matchup
from fetch_lineups import get_pitcher_hand, get_lineup_for_game
from monte_carlo_f5 import run_monte_carlo_f5
from full_game_model import run_full_game_mc

def get_advice(line, td_total, under_prob, td_only=False):
    td_gap = line - td_total
    td_signal = 'UNDER' if td_gap > 0 else 'OVER'
    if td_only:
        return td_signal, 'TD-ONLY'
    if under_prob >= 0.52:
        mc_signal = 'UNDER'
    elif under_prob <= 0.48:
        mc_signal = 'OVER'
    else:
        mc_signal = 'NEUTRAL'
    if td_signal == mc_signal:
        mc_strong = under_prob >= 0.58 or under_prob <= 0.42
        td_strong = abs(td_gap) >= 0.30
        confidence = 'HIGH' if (mc_strong and td_strong) else 'MODERATE'
        return f'Bet {mc_signal} ({confidence})'
    return 'Skip'

def run():
    # Backtest dates
    start_date = datetime.date(2026, 6, 24)
    end_date = datetime.date(2026, 6, 24)
    
    current_date = start_date
    delta = datetime.timedelta(days=1)
    
    traps_avoided = 0
    wins_lost = 0
    asym_flags = 0
    asym_losses = 0
    total_bets = 0
    
    print("Starting backtest from", start_date, "to", end_date)
    
    while current_date <= end_date:
        d_str = current_date.strftime("%Y-%m-%d")
        print(f"\n--- {d_str} ---")
        games = get_today_games(1, date_str=d_str)
        if not games:
            current_date += delta
            continue
            
        for g in games:
            away, home, venue, gid = g['away_team'], g['home_team'], g['venue_name'], g['game_id']
            ap, hp = g['away_pitcher'], g['home_pitcher']
            if not ap or not hp or ap == 'TBD' or hp == 'TBD':
                continue
            
            actual_runs = get_actual_f5_score(gid)
            if actual_runs is None: continue
            
            ap_fip = get_historical_pitcher_fip(ap, d_str) or 4.0
            hp_fip = get_historical_pitcher_fip(hp, d_str) or 4.0
            away_bp = get_historical_team_bullpen_fip(away, d_str) or 4.0
            home_bp = get_historical_team_bullpen_fip(home, d_str) or 4.0
            away_wrc = get_historical_team_wrc(away, d_str) or 100
            home_wrc = get_historical_team_wrc(home, d_str) or 100
            ap_ip = get_historical_pitcher_avg_ip(ap, d_str) or 5.0
            hp_ip = get_historical_pitcher_avg_ip(hp, d_str) or 5.0
            ap_hand = get_pitcher_hand(ap, sport_id=1)
            hp_hand = get_pitcher_hand(hp, sport_id=1)
            
            pf_details = get_park_factor_details(venue)
            pf = pf_details.get('static', 1.0)
            realized_pf = pf_details.get('realized', 1.0)
            
            weather = get_historical_weather(gid) or {'temp_multiplier': 1.0, 'wind_multiplier': 1.0, 'weather_multiplier': 1.0, 'temp_fatigue_scaler': 1.0, 'weather_label': ''}
            weather_mult = weather.get('weather_multiplier', 1.0)
            
            ump_name = get_historical_umpire_for_game(gid)
            ump_profile = get_historical_umpire_profile(ump_name, d_str) if ump_name else None
            
            td = grade_matchup(away, ap_fip, away_bp, ap_ip, away_wrc, home, hp_fip, home_bp, hp_ip, home_wrc, pf, weather_mult, ap_hand, hp_hand)
            td_total = td['projected_f5_total']
            
            lineups = get_lineup_for_game(gid)
            mc = run_monte_carlo_f5(lineups['away'], lineups['home'], g.get('away_pitcher_id'), g.get('home_pitcher_id'), ap_fip, hp_fip, 100, pf, weather, 1, ap_hand, hp_hand, ump_profile, away_wrc, home_wrc)
            fg_mc = run_full_game_mc(
                lineups['away'], lineups['home'],
                ap, hp,
                ap_fip, hp_fip,
                away, home,
                ap_ip, hp_ip,
                iterations=100,
                park_factor=pf,
                weather_context=weather,
                sport_id=1,
                away_pitcher_hand=ap_hand,
                home_pitcher_hand=hp_hand,
                umpire_profile=ump_profile,
                away_wrc=away_wrc,
                home_wrc=home_wrc
            )
            mc['full_game_total'] = fg_mc['full_game_total']
            
            adv_4_5 = get_advice(4.5, td_total, mc['under_4_5_prob'])
            if 'Skip' in adv_4_5:
                continue
                
            orig_bet = 'OVER' if 'OVER' in adv_4_5 else 'UNDER'
            total_bets += 1
            is_win = (orig_bet == 'OVER' and actual_runs > 4.5) or (orig_bet == 'UNDER' and actual_runs < 4.5)
            
            # Filters
            pf_diff = realized_pf - pf
            is_hitter_bias = pf_diff > 0.15
            is_pitcher_bias = pf_diff < -0.15
            
            team_bias_skip = (orig_bet == 'OVER' and is_hitter_bias) or (orig_bet == 'UNDER' and is_pitcher_bias)
            
            is_roof_closed = weather.get('weather_label', '').lower() in ['dome', 'roof closed']
            is_roof_park = any(p in venue.lower() for p in ['daikin', 'chase', 'globe life', 'minute maid'])
            roof_skip = is_roof_closed and is_roof_park and orig_bet == 'OVER'
            
            f5_ratio = mc['mc_total_runs'] / max(0.1, mc['full_game_total'])
            asym_warn = not (0.51 <= f5_ratio <= 0.53)
            
            if asym_warn:
                asym_flags += 1
                if not is_win: asym_losses += 1
                
            if team_bias_skip or roof_skip:
                if not is_win:
                    traps_avoided += 1
                    print(f"  [TRAP AVOIDED] {away} @ {home}: {orig_bet} 4.5 | Act: {actual_runs} (Bias: {team_bias_skip}, Roof: {roof_skip})")
                else:
                    wins_lost += 1
                    print(f"  [WIN LOST] {away} @ {home}: {orig_bet} 4.5 | Act: {actual_runs} (Bias: {team_bias_skip}, Roof: {roof_skip})")
                    
        current_date += delta
        
    print(f"\n--- Results ---")
    print(f"Total Bets Initially Recommended: {total_bets}")
    print(f"Traps Avoided (Losses prevented by new skips): {traps_avoided}")
    print(f"Wins Lost (Wins blocked by new skips): {wins_lost}")
    print(f"Asymmetric Warnings Triggered: {asym_flags} (Losses: {asym_losses})")

if __name__ == '__main__':
    run()
