import requests
import json

def check_nbl_deep():
    h = {'Origin':'https://nbl.com.au','Referer':'https://nbl.com.au/'}
    url = 'https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/2025/all'
    r = requests.get(url, headers=h)
    data = r.json().get("data", [])
    print(f"Total matches in NBL 2025: {len(data)}")
    if data:
        # Check years present
        years = set()
        for m in data:
            st = m.get("start_time", "")
            if st: years.add(st[:4])
        print(f"Years found in NBL 2025 matches: {years}")
        
    # Check 2024
    url = 'https://prod.rosetta.nbl.com.au/get/nbl/matches/in/season/2024/all'
    r = requests.get(url, headers=h)
    data = r.json().get("data", [])
    print(f"Total matches in NBL 2024: {len(data)}")
    if data:
        years = set()
        for m in data:
            st = m.get("start_time", "")
            if st: years.add(st[:4])
        print(f"Years found in NBL 2024 matches: {years}")

def check_acb_auth():
    # Try different referers
    referers = [
        'https://acb.com/',
        'https://www.acb.com/',
        'https://www.acb.com/jornada/temporada/2025/edicion/90/jornada/16'
    ]
    url = 'https://api2.acb.com/api/v1/openapilive/Matches/matchesbymatchweeklite?idCompetition=1&idEdition=90&idMatchweek=5899'
    key = '0dd94928-6f57-4c08-a3bd-b1b2f092976e'
    
    for ref in referers:
        h = {
            'Origin': 'https://www.acb.com',
            'Referer': ref,
            'x-apikey': key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        try:
            r = requests.get(url, headers=h)
            print(f"ACB Ref: {ref} -> Status: {r.status_code}")
            if r.status_code == 200:
                print("SUCCESS!")
                break
        except:
            pass

if __name__ == "__main__":
    print("--- NBL DEEP CHECK ---")
    check_nbl_deep()
    print("\n--- ACB AUTH CHECK ---")
    check_acb_auth()
