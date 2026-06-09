import statsapi
import sys
import json

sys.path.insert(0, 'mlb')
from fetch_probables import get_probable_starters
from fetch_metrics import fetch_daily_metrics
from fetch_lineups import fetch_all_lineups, get_pitcher_hand
from park_factors import get_effective_pf
from grade_f5 import grade_matchup
from grade_reports import get_actual_f5

def main():
    date_str = '06/06/2026'
    print(f"Grading Top-Down Math for Current Model on {date_str}...")
    
    games = statsapi.schedule(sportId=1, date=date_str)
    metrics = fetch_daily_metrics()
    
    # We only need enough info for Top-Down math
    
    results = []
    wins = 0
    losses = 0
    
    for g in games:
        game_id = g['game_id']
        away = g['away_name']
        home = g['home_name']
        
        actual_score = get_actual_f5(game_id)
        if actual_score is None:
            continue
        actual_total = actual_score[0] + actual_score[1]
        
        starters = get_probable_starters(game_id)
        if not starters['away']['id'] or not starters['home']['id']:
            continue
            
        away_pitcher_id = starters['away']['id']
        home_pitcher_id = starters['home']['id']
        
        away_pitcher_hand = get_pitcher_hand(away_pitcher_id)
        home_pitcher_hand = get_pitcher_hand(home_pitcher_id)
        
        venue_id = g['venue_id']
        effective_pf, weather_multiplier, weather_ctx = get_effective_pf(venue_id, date_str)
        
        matchup_data = {
            'game_id': game_id,
            'away_team_id': g['away_id'],
            'home_team_id': g['home_id'],
            'away_pitcher_id': away_pitcher_id,
            'home_pitcher_id': home_pitcher_id,
            'away_pitcher_hand': away_pitcher_hand,
            'home_pitcher_hand': home_pitcher_hand,
            'weather_multiplier': weather_multiplier
        }
        
        try:
            td_total, raw_away, raw_home = grade_matchup(matchup_data, metrics, effective_pf)
            
            # Grade against 4.5 line
            projected_over = td_total > 4.5
            actual_over = actual_total > 4.5
            
            # If actual == 4 or 5 and we missed, we can check. 
            # But let's just do a strict > 4.5 check.
            # If actual is 4.5 (impossible), but let's say:
            if projected_over and actual_total >= 5:
                res = "WIN"
                wins += 1
            elif not projected_over and actual_total <= 4:
                res = "WIN"
                wins += 1
            else:
                res = "LOSS"
                losses += 1
                
            print(f"{away} @ {home}")
            print(f"  Projected: {td_total:.2f} | Actual: {actual_total} -> {res}")
        except Exception as e:
            print(f"Error on {game_id}: {e}")
            
    print(f"\nFINAL GRADE: {wins}-{losses} ({wins/(wins+losses)*100:.1f}%)")

if __name__ == "__main__":
    main()
