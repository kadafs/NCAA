import requests
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://barttorvik.com/"
}
url = "https://barttorvik.com/trank.php?year=2026&json=1"
try:
    resp = requests.get(url, headers=headers, timeout=15)
    print(f"Status: {resp.status_code}")
    print(f"Content Length: {len(resp.text)}")
    if resp.status_code == 200:
        if "Verifying browser" in resp.text:
            print("Blocked by browser verification.")
        else:
            print("Successfully fetched data!")
            print(f"Sample: {resp.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
