import requests
import json

url = "https://api2.acb.com/api/seasondata/Competition/standings?competitionId=1&editionId=90&roundId=5899"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
    "Origin": "https://acb.com",
    "Referer": "https://acb.com/",
    "Accept": "application/json",
    "x-apikey": "0dd94928-6f57-4c08-a3bd-b1b2f092976e"
}

try:
    response = requests.get(url, headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Success! ACB Standings preview:")
        print(json.dumps(data, indent=2)[:500])
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")
