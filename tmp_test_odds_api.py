import requests
import os
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("API_BASKETBALL_KEY")
base = "https://v1.basketball.api-sports.io"
headers = {"x-apisports-key": key}

# 1. Check account status
r = requests.get(f"{base}/status", headers=headers, timeout=10)
status = r.json()
print("=== ACCOUNT STATUS ===")
print(json.dumps(status.get("response", {}), indent=2))
print(f"Remaining calls today: {r.headers.get('x-ratelimit-requests-remaining', 'N/A')}")

# 2. Check /bets endpoint (all available bet types)
r2 = requests.get(f"{base}/bets", headers=headers, timeout=10)
bets = r2.json()
print("\n=== AVAILABLE BET TYPES ===")
for b in bets.get("response", []):
    print(f"  id={b['id']:3d}  {b['name']}")

# 3. Try /odds for NBA (league=12, season=2024-2025, bet=4=Over/Under)
r3 = requests.get(f"{base}/odds", headers=headers, params={"league": 12, "season": "2024-2025", "bet": 4}, timeout=10)
odds = r3.json()
print("\n=== /odds (NBA league=12, bet=4 Over/Under) ===")
print(f"Results: {odds.get('results', 0)}")
print(f"Errors: {odds.get('errors', [])}")
resp = odds.get("response", [])
if resp:
    print(json.dumps(resp[0], indent=2))
else:
    print("(no data returned)")

# 4. Also try bookmakers
r4 = requests.get(f"{base}/bookmakers", headers=headers, timeout=10)
bm = r4.json()
print("\n=== BOOKMAKERS ===")
for b in bm.get("response", [])[:10]:
    print(f"  id={b['id']:3d}  {b['name']}")
