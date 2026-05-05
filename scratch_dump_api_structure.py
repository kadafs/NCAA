"""
Dumps the full raw Sportradar API structure for an NBL1 fixture
so we can identify the correct field paths for date and player stats.
"""
import requests, json, re, time
from playwright.sync_api import sync_playwright

SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Referer': 'https://nbl1.com.au/',
    'Origin': 'https://nbl1.com.au',
    'Accept': 'application/json',
}

# Get live UUIDs from the page
print("[*] Fetching UUIDs via Playwright...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://nbl1.com.au/fixtures", wait_until='domcontentloaded', timeout=60000)
    try:
        page.wait_for_load_state('networkidle', timeout=25000)
    except:
        pass
    page.wait_for_timeout(3000)
    html = page.content()
    browser.close()

uuids = list(set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', html.lower())))
print(f"[*] Got {len(uuids)} UUIDs. Scanning for a completed fixture...")

# Try UUIDs until we find one that's a completed NBL1 game with stats
COMPETITION_MAP = {
    "NBL1 South Men", "NBL1 South Women", "NBL1 North Men", "NBL1 North Women",
    "NBL1 East Men", "NBL1 East Women", "NBL1 Central Men", "NBL1 Central Women",
    "NBL1 West Men", "NBL1 West Women",
}

found = False
for uid in uuids[:200]:
    try:
        res = requests.get(SPORTRADAR_URL.format(uid), headers=HEADERS, timeout=10)
        if res.status_code != 200:
            continue
        data = res.json().get('data', {})
        banner = data.get('banner', {})
        comp = banner.get('competition', {})
        comp_name = comp.get('name', '')
        if comp_name not in COMPETITION_MAP:
            continue

        # Check if this game has statistics (i.e., it's been played)
        stats = data.get('statistics', {})
        fixture_top = data.get('fixture', {})
        
        print(f"\nFOUND NBL1 FIXTURE: {uid}")
        print(f"  Competition: {comp_name}")
        print(f"  Has top-level 'statistics'? {bool(stats)}")
        print(f"  Has top-level 'fixture'? {bool(fixture_top)}")
        if fixture_top:
            print(f"  Top-level fixture keys: {list(fixture_top.keys())[:15]}")
        
        banner_fixture = banner.get('fixture', {})
        print(f"\n  banner.fixture keys: {list(banner_fixture.keys())[:15]}")
        
        if stats:
            print(f"\n  statistics keys: {list(stats.keys())}")
            stats_data = stats.get('data', {})
            print(f"  statistics.data keys: {list(stats_data.keys())}")
            base = stats_data.get('base', {})
            print(f"  statistics.data.base keys: {list(base.keys())}")
            home = base.get('home', {})
            print(f"  statistics.data.base.home keys: {list(home.keys())[:10]}")
            persons = home.get('persons', [])
            print(f"  persons count: {len(persons)}")
            if persons:
                print(f"  persons[0] keys: {list(persons[0].keys())}")
                rows = persons[0].get('rows', [])
                print(f"  rows count: {len(rows)}")
                if rows:
                    print(f"  rows[0] keys: {list(rows[0].keys())}")
                    print(f"  rows[0].statistics: {rows[0].get('statistics', {})}")
                    print(f"  rows[0].participated: {rows[0].get('participated')}")
        
        # Save full response for manual inspection
        with open('scratch_api_response_dump.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\n  [+] Full response saved to scratch_api_response_dump.json")
        found = True
        break
    except Exception as e:
        print(f"  Skip {uid}: {e}")
        time.sleep(0.5)
        continue

if not found:
    print("\n[!] No completed NBL1 game found in first 200 UUIDs")
    print("    This likely means the NBL1 2026 season hasn't started yet!")
