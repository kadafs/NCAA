import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
HEADERS = {
    "x-rapidapi-host": "v1.baseball.api-sports.io",
    "x-rapidapi-key": API_KEY
}

def test_kbo_teams():
    url = "https://v1.baseball.api-sports.io/teams"
    params = {"league": 5, "season": 2026}
    
    response = requests.get(url, headers=HEADERS, params=params)
    print("TEAMS RESPONSE:")
    print(json.dumps(response.json(), indent=2))

if __name__ == '__main__':
    test_kbo_teams()
