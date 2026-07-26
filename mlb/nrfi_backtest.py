import os
import statsapi
from datetime import datetime, timedelta
from nrfi_data import get_pitcher_first_inning_stats, get_batter_xwoba_vs_hand
from nrfi_model import evaluate_game
from nrfi_engine import get_top_3_hitters

def run_backtest(start_date, end_date):
    print(f"Running NRFI Backtest from {start_date} to {end_date}...\n")
    
    current_date = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    total_games = 0
    strong_nrfi_wins = 0
    strong_nrfi_losses = 0
    strong_yrfi_wins = 0
    strong_yrfi_losses = 0
    
    while current_date <= end:
        date_str = current_date.strftime('%Y-%m-%d')
        print(f"Processing Slate: {date_str}")
        
        schedule = statsapi.schedule(date=date_str, sportId=1)
        for game in schedule[:3]:
            game_pk = game['game_id']
            away_team = game['away_name']
            home_team = game['home_name']
            
            # Check actual results first to save API calls if game was cancelled
            if game['status'] not in ['Final', 'Completed Early']:
                continue
                
            try:
                # Did they score in the 1st?
                boxscore = statsapi.get('game', {'gamePk': game_pk})
                linescore = boxscore.get('liveData', {}).get('linescore', {})
                innings = linescore.get('innings', [])
                
                if not innings:
                    continue
                    
                first_inning = innings[0]
                away_runs = first_inning.get('away', {}).get('runs', 0)
                home_runs = first_inning.get('home', {}).get('runs', 0)
                
                # Check for None just in case
                away_runs = away_runs if away_runs is not None else 0
                home_runs = home_runs if home_runs is not None else 0
                
                runs_scored = away_runs + home_runs
                is_yrfi = runs_scored > 0
                is_nrfi = runs_scored == 0
                
                # Now fetch predictions
                probables = boxscore.get('gameData', {}).get('probablePitchers', {})
                away_sp_id = probables.get('away', {}).get('id')
                home_sp_id = probables.get('home', {}).get('id')
                
                if not away_sp_id or not home_sp_id:
                    continue
                    
                away_sp_throws = statsapi.get('people', {'personIds': away_sp_id}).get('people', [])[0].get('pitchHand', {}).get('code', 'R')
                home_sp_throws = statsapi.get('people', {'personIds': home_sp_id}).get('people', [])[0].get('pitchHand', {}).get('code', 'R')
                
                # We need data UP TO THIS DATE to be perfectly accurate in a true backtest, 
                # but for speed in this prototype we will use their overall 2026 data.
                # A full backtest would pass 'end_date=date_str' to the data functions.
                # Let's pass the date to prevent data leakage!
                
                away_sp_stats = get_pitcher_first_inning_stats(away_sp_id, end_date=date_str)
                home_sp_stats = get_pitcher_first_inning_stats(home_sp_id, end_date=date_str)
                
                away_top_3 = get_top_3_hitters(game_pk, 'away')
                home_top_3 = get_top_3_hitters(game_pk, 'home')
                
                if not away_top_3 or not home_top_3:
                    continue
                    
                away_hitters_stats = []
                for h in away_top_3:
                    stat = get_batter_xwoba_vs_hand(h['id'], home_sp_throws, end_date=date_str)
                    if stat:
                        away_hitters_stats.append(stat)
                        
                home_hitters_stats = []
                for h in home_top_3:
                    stat = get_batter_xwoba_vs_hand(h['id'], away_sp_throws, end_date=date_str)
                    if stat:
                        home_hitters_stats.append(stat)
                        
                evaluation = evaluate_game(away_hitters_stats, home_sp_stats, home_hitters_stats, away_sp_stats)
                rec = evaluation['recommendation']
                
                total_games += 1
                
                if rec == "STRONG NRFI":
                    if is_nrfi:
                        strong_nrfi_wins += 1
                    else:
                        strong_nrfi_losses += 1
                        
                elif rec == "STRONG YRFI":
                    if is_yrfi:
                        strong_yrfi_wins += 1
                    else:
                        strong_yrfi_losses += 1
                        
            except Exception as e:
                pass
                
        current_date += timedelta(days=1)
        
    print("\n=== BACKTEST RESULTS ===")
    print(f"Total Games Evaluated: {total_games}")
    
    total_strong_nrfi = strong_nrfi_wins + strong_nrfi_losses
    if total_strong_nrfi > 0:
        nrfi_win_pct = (strong_nrfi_wins / total_strong_nrfi) * 100
        print(f"STRONG NRFI: {strong_nrfi_wins}W - {strong_nrfi_losses}L ({nrfi_win_pct:.1f}%)")
    else:
        print("STRONG NRFI: No games triggered.")
        
    total_strong_yrfi = strong_yrfi_wins + strong_yrfi_losses
    if total_strong_yrfi > 0:
        yrfi_win_pct = (strong_yrfi_wins / total_strong_yrfi) * 100
        print(f"STRONG YRFI: {strong_yrfi_wins}W - {strong_yrfi_losses}L ({yrfi_win_pct:.1f}%)")
    else:
        print("STRONG YRFI: No games triggered.")

if __name__ == "__main__":
    # Run a 1-day backtest to verify model logic quickly
    run_backtest('2026-07-25', '2026-07-25')
