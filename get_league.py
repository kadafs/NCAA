import os
import requests
from dotenv import load_dotenv

load_dotenv('C:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/.env')
key = os.getenv('API_FOOTBALL_KEY')
if not key:
    key = os.getenv('API_SPORTS_KEY')
    
headers = {
    'x-rapidapi-host': "v3.football.api-sports.io",
    'x-rapidapi-key': key
}

response = requests.request("GET", "https://v3.football.api-sports.io/leagues?id=667", headers=headers)
data = response.json()
if 'response' in data and len(data['response']) > 0:
    league = data['response'][0]
    print(f"League 667 is: {league['league']['name']} ({league['country']['name']})")
else:
    print("Not found in API Football.")
