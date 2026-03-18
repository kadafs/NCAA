import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")

BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {"x-apisports-key": API_KEY}

def get(endpoint, params):
    r = requests.get(BASE_URL + endpoint, headers=HEADERS, params=params)
    return r.json()

def main():
    print("Fetching Team Stats (Sydney)...")
    stats = get("/teams/statistics", {"team": 943, "league": 188, "season": 2025})
    
    print("Fetching H2H...")
    h2h = get("/fixtures/headtohead", {"h2h": "943-945", "last": 5})
    
    print("Fetching Standings...")
    standings = get("/standings", {"league": 188, "season": 2025})

    with open("data/api_inspection.json", "w") as f:
        json.dump({
            "stats": stats,
            "h2h": h2h,
            "standings": standings
        }, f, indent=2)
        
    print("Data dumped to data/api_inspection.json")

if __name__ == "__main__":
    main()
