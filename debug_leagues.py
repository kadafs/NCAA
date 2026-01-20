import requests
import json

def check_nbl():
    h = {'Origin':'https://nbl.com.au','Referer':'https://nbl.com.au/'}
    for season in ["2025", "2026"]:
        url = f'https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/{season}/all'
        try:
            r = requests.get(url, headers=h)
            if r.status_code == 200:
                matches = r.json().get("data", [])
                print(f"Season {season} has {len(matches)} games.")
                if matches:
                    print(f"First match start: {matches[0].get('start_time')}")
                    print(f"Last match start: {matches[-1].get('start_time')}")
                    # Check for any Jan 2026 games
                    jan_2026 = [m for m in matches if '2026-01' in (m.get('start_time') or '')]
                    print(f"Season {season} has {len(jan_2026)} games in Jan 2026.")
        except:
            print(f"Season {season} failed.")

def check_acb():
    h = {'Origin':'https://acb.com','Referer':'https://acb.com/','x-apikey':'0dd94928-6f57-4c08-a3bd-b1b2f092976e'}
    url = 'https://api2.acb.com/api/seasondata/Competition/standings?competitionId=1&editionId=90&roundId=5899'
    r = requests.get(url, headers=h)
    data = r.json()
    # Check if there's any record in common fields
    print("ACB Sample Object keys:", data.get("standings", [{}])[0].keys())
    # Search for common record keywords in the whole JSON
    s = json.dumps(data).lower()
    for word in ["victoria", "derrota", "ganado", "perdido", "jugado", "puntos", "won", "lost", "played"]:
        if word in s:
            print(f"ACB: Found '{word}' in JSON")

if __name__ == "__main__":
    print("--- NBL Check ---")
    check_nbl()
    print("\n--- ACB Check ---")
    check_acb()
