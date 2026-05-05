import requests, json

SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Referer': 'https://nbl1.com.au/',
    'Origin': 'https://nbl1.com.au',
}

# These are CONFIRMED (completed) NBL1 games from the results test
confirmed_uuids = [
    ("9169cd45-d6e8-11f0-a9c0-cfb7d5472bba", "2026-04-24"),
    ("6af07794-d3dd-11f0-a3df-056d5acb892b", "2026-04-02"),
    ("2422f919-da64-11f0-8a63-1f4631345f86", "2026-05-02"),
]

for uid, date in confirmed_uuids:
    print(f"\nTesting CONFIRMED game {uid} ({date})...")
    try:
        res = requests.get(SPORTRADAR_URL.format(uid), headers=HEADERS, timeout=15)
        print(f"  Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json().get('data', {})
            fixture_top = data.get('fixture', {})
            status = fixture_top.get('status')
            start = fixture_top.get('startTimeLocal', '')
            
            banner = data.get('banner', {})
            comp = banner.get('competition', {})
            comp_name = comp.get('name', 'N/A')
            competitors = banner.get('fixture', {}).get('competitors', [])
            home = next((c.get('name') for c in competitors if c.get('isHome')), 'N/A')
            away = next((c.get('name') for c in competitors if not c.get('isHome')), 'N/A')
            
            print(f"  API Status: {status}, Competition: {comp_name}")
            print(f"  Teams: {home} vs {away}")
            
            stats_base = data.get('statistics', {}).get('data', {}).get('base', {})
            home_data = stats_base.get('home', {})
            persons = home_data.get('persons', [])
            total_rows = sum(len(g.get('rows', [])) for g in persons)
            
            print(f"  persons groups: {len(persons)}, total rows: {total_rows}")
            if persons and persons[0].get('rows'):
                row = persons[0]['rows'][0]
                print(f"  Sample row keys: {list(row.keys())}")
                s = row.get('statistics', {})
                print(f"  Sample stats keys: {list(s.keys())[:10]}")
                print(f"  minutes value: {s.get('minutes')}")
                print(f"  participated: {row.get('participated')}")
                print(f"  points: {s.get('points')}")
    except Exception as e:
        print(f"  Error: {e}")
