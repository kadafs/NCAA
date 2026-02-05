import requests
from datetime import datetime, timedelta

def dump_range():
    for i in range(-1, 2): # -1, 0, 1 from Feb 4th
        target_date = datetime(2026, 2, 4) + timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")
        year, month, day = target_date.year, target_date.month, target_date.day
        url = f"https://ncaa-api-w2ry.onrender.com/scoreboard/basketball-men/d1/{year}/{month:02d}/{day:02d}"
        
        try:
            resp = requests.get(url, timeout=10)
            data = resp.json()
            games = data.get('games', [])
            print(f"Date: {date_str} | Games: {len(games)}")
            if games:
                print(f"  Sample: {games[0]['game']['away']['names']['short']} @ {games[0]['game']['home']['names']['short']}")
                # Look for Michigan or Penn State
                for g in games:
                    s = str(g).lower()
                    if "michigan" in s or "penn" in s:
                        print(f"  FOUND: {g['game']['away']['names']['short']} @ {g['game']['home']['names']['short']} | Status: {g['game']['gameState']}")
        except:
            print(f"Date: {date_str} | Failed")

if __name__ == "__main__":
    dump_range()
