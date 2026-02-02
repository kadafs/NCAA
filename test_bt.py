import requests
import json

url = "https://api.actionnetwork.com/web/v1/scoreboard/ncaab?division=D1"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.actionnetwork.com/"
}

try:
    res = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        games = data.get("games", [])
        print(f"Total Games found with division=D1: {len(games)}")
        for i, game in enumerate(games):
            teams = game.get("teams", [])
            away = next((t for t in teams if t['id'] == game['away_team_id']), {})
            home = next((t for t in teams if t['id'] == game['home_team_id']), {})
            print(f"Game {i+1}: {away.get('full_name')} vs {home.get('full_name')}")
            if i >= 10: break
except Exception as e:
    print(f"Error: {e}")
