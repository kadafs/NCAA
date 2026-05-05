import requests, re, json

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

# Fetch fixtures.js to find the API endpoint pattern
print("=== Fetching fixtures.js ===")
r = requests.get('https://nbl1-webflow.s3.ap-southeast-2.amazonaws.com/prod/fixtures.js', headers=headers, timeout=15)
print(f"Status: {r.status_code}, Size: {len(r.text)}")

js = r.text

# Look for rosetta.nbl1.com.au API patterns
print("\n=== Searching for rosetta API patterns ===")
api_patterns = re.findall(r'["\']([^"\']*rosetta[^"\']*)["\']', js)
for p in api_patterns[:20]:
    print(f"  {p}")

# Look for fetch/XMLHttpRequest patterns
print("\n=== Searching for fetch/URL patterns ===")
fetches = re.findall(r'fetch\(["`]([^"`]+)["`]', js)
for f in fetches[:20]:
    print(f"  fetch: {f}")

urls = re.findall(r'https?://[^\s"\'`<>]+', js)
for u in urls[:30]:
    print(f"  URL: {u}")

# Look for fixture/game specific keys
print("\n=== Searching for fixture-related keywords ===")
for kw in ['fixtureId', 'fixture_id', 'externalMatch', 'matchId', 'gameId', '/games/', 'season']:
    positions = [m.start() for m in re.finditer(kw, js, re.IGNORECASE)]
    if positions:
        pos = positions[0]
        print(f"\n  '{kw}' found {len(positions)} times. First context:")
        print(f"  ...{js[max(0,pos-100):pos+200]}...")
