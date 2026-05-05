"""
Try the NBL1 results page to find completed game UUIDs
and check what status codes completed games have.
"""
import re, requests, json, time
from playwright.sync_api import sync_playwright

SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36',
    'Referer': 'https://nbl1.com.au/',
    'Origin': 'https://nbl1.com.au',
}

COMPETITION_MAP = {
    "NBL1 South Men", "NBL1 South Women", "NBL1 North Men", "NBL1 North Women",
    "NBL1 East Men", "NBL1 East Women", "NBL1 Central Men", "NBL1 Central Women",
    "NBL1 West Men", "NBL1 West Women",
}

# Try different NBL1 URL paths - results, scores, etc.
urls_to_try = [
    "https://nbl1.com.au/results",
    "https://nbl1.com.au/scores",
    "https://nbl1.com.au/competitions",
    "https://nbl1.com.au/fixtures?tab=results",
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    
    for test_url in urls_to_try:
        print(f"\n[*] Trying: {test_url}")
        try:
            page = browser.new_page()
            page.goto(test_url, wait_until='domcontentloaded', timeout=60000)
            try:
                page.wait_for_load_state('networkidle', timeout=20000)
            except:
                pass
            page.wait_for_timeout(3000)
            html = page.content()
            page.close()
            
            uuids = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', html.lower()))
            print(f"  Found {len(uuids)} UUIDs")
            
            # Test first few for completed games
            for uid in list(uuids)[:30]:
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
                    fixture_top = data.get('fixture', {})
                    status = fixture_top.get('status', '')
                    start_time = fixture_top.get('startTimeLocal', '')
                    has_stats = bool(data.get('statistics', {}).get('data', {}).get('base', {}))
                    print(f"  NBL1 UUID {uid}: status={status}, start={start_time[:10]}, has_stats={has_stats}")
                except Exception as e:
                    pass
        except Exception as e:
            print(f"  Failed: {e}")
    
    browser.close()
