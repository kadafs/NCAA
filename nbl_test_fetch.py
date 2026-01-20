import requests
import json

url = "https://prod.rosetta.nbl.com.au/get/nbl/standings/2025/regular"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Origin": "https://www.nbl.com.au",
    "Referer": "https://www.nbl.com.au/",
    "Accept": "*/*",
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Success! Data preview:")
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f"Error: {response.text}")

    # Check Games
    games_url = "https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/2025/all"
    res_games = requests.get(games_url, headers=headers)
    print(f"\nGames Code: {res_games.status_code}")
    if res_games.status_code == 200:
        print("Success! Games preview:")
        print(json.dumps(res_games.json(), indent=2)[:500])

except Exception as e:
    print(f"Exception: {e}")
