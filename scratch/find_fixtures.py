import re
import requests
import json

def find_fixtures():
    url = "https://nbl1.com.au/fixtures?tab=results"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    
    # Try to find fixtureId in JSON strings
    matches = re.findall(r'"fixtureId":"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"', res.text.lower())
    print(f"Found {len(matches)} fixtureId matches")
    for m in matches[:5]:
        print(f"  {m}")

    # Check for competition names to see if we are in the right place
    comps = re.findall(r'"competitionName":"([^"]+)"', res.text)
    print(f"Found {len(comps)} competition matches")
    for c in set(comps):
        print(f"  {c}")

if __name__ == "__main__":
    find_fixtures()
