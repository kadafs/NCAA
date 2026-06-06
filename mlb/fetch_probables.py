import pybaseball
from pybaseball import schedule_and_record, team_game_logs
from datetime import datetime
import pandas as pd

def get_today_games():
    """
    Fetches today's MLB schedule and probable pitchers using pybaseball/statsapi.
    Currently, pybaseball's schedule_and_record gets past results, but to get future/today's
    probable pitchers reliably without an API key, we use the free mlb statsapi endpoints directly
    or pybaseball's statsapi wrapper if available.
    """
    import statsapi
    
    today = datetime.now().strftime("%m/%d/%Y")
    print(f"Fetching MLB schedule for {today}...")
    
    try:
        # Get games for today
        schedule = statsapi.schedule(date=today)
        games = []
        
        for game in schedule:
            game_id = game['game_id']
            away_team = game['away_name']
            home_team = game['home_name']
            
            # Probable pitchers
            away_pitcher = game.get('away_probable_pitcher', 'TBD')
            home_pitcher = game.get('home_probable_pitcher', 'TBD')
            
            game_time = game.get('game_datetime', '')
            status = game.get('status', 'Unknown')
            
            game_info = {
                'game_id': game_id,
                'time': game_time,
                'status': status,
                'away_team': away_team,
                'home_team': home_team,
                'away_pitcher': away_pitcher,
                'home_pitcher': home_pitcher
            }
            games.append(game_info)
            
        return games
    except Exception as e:
        print(f"Error fetching schedule: {e}")
        return []

if __name__ == "__main__":
    games = get_today_games()
    if not games:
        print("No games found or error occurred.")
    else:
        print(f"Found {len(games)} games:")
        for g in games:
            print(f"{g['away_team']} ({g['away_pitcher']}) @ {g['home_team']} ({g['home_pitcher']}) - {g['time']}")
