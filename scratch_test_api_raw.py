import requests, json, re
from playwright.sync_api import sync_playwright

URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"

print("[*] Fetching live UUIDs from NBL1 page...")
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
print(f"[*] Got {len(uuids)} UUIDs. Testing first 5 raw API responses...\n")

for uid in uuids[:5]:
    url = URL.format(uid)
    res = requests.get(url, timeout=10)
    print(f"UUID: {uid}")
    print(f"  Status: {res.status_code}")
    if res.status_code == 200:
        try:
            data = res.json()
            # Show top-level keys
            top_keys = list(data.keys())
            print(f"  Top-level keys: {top_keys}")
            inner = data.get('data', {})
            print(f"  data keys: {list(inner.keys())[:10]}")
            banner = inner.get('banner', {})
            comp = banner.get('competition', {})
            comp_name = comp.get('name', 'N/A')
            print(f"  Competition: {comp_name}")
            stats = inner.get('statistics', {})
            print(f"  Has statistics: {bool(stats)}")
        except Exception as e:
            print(f"  Parse error: {e}")
    print()
