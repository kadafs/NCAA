from nba_api.stats.endpoints import scoreboardv3
from datetime import datetime, timedelta
import json

def test_nba_api():
    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    print(f"Testing NBA Scoreboard for {date_str}...")
    try:
        sb = scoreboardv3.ScoreboardV3(game_date=date_str, timeout=30)
        data = sb.get_dict()
        games = data.get('scoreboard', {}).get('games', [])
        print(f"Found {len(games)} games.")
        if games:
            print("First game full structure:")
            print(json.dumps(games[0], indent=2))
            for g in games:
                print(f"Game: {g['awayTeam']['teamName']} @ {g['homeTeam']['teamName']} - Status: {g.get('gameStatusText')} (ID: {g.get('gameStatus')})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nba_api()
