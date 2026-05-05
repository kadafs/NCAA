import requests, json

uid = "6af07794-d3dd-11f0-a3df-056d5acb892b"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Referer': 'https://nbl1.com.au/',
}
res = requests.get(f"https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={uid}", headers=HEADERS, timeout=15)
data = res.json().get('data', {})
stats_base = data.get('statistics', {}).get('data', {}).get('base', {})
home_data = stats_base.get('home', {})
persons = home_data.get('persons', [])

# Find a participated player
for group in persons:
    for row in group.get('rows', []):
        if row.get('participated'):
            print("PARTICIPATING player keys:", list(row.keys()))
            s = row.get('statistics', {})
            print("ALL stats keys:", list(s.keys()))
            print("Sample stats:", json.dumps(s, indent=2)[:1000])
            break
    break
