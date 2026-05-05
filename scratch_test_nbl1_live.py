import json, re, requests

# Test the Sportradar API directly with a few UUIDs from the fixture page
# to see if any return valid game data

# Load a sample of the last-known valid UUIDs from whatever cache we have
import glob

# Test the extract_box_score function directly
import sys
sys.path.insert(0, '.')
from scrape_nbl1 import extract_box_score

# Try testing a few UUIDs manually
test_uuids = [
    "some-uuid-to-test"
]

# Actually - let's fetch the NBL1 page now and test the first 20 UUIDs live
from playwright.sync_api import sync_playwright

print("[*] Fetching NBL1 page to get live UUIDs...")
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
print(f"[*] Found {len(uuids)} UUIDs on page")
print("[*] Testing first 20 UUIDs against Sportradar API...")

found = 0
for i, uid in enumerate(uuids[:20]):
    result = extract_box_score(uid)
    if result:
        found += 1
        print(f"  UUID {i}: VALID GAME! {result.get('home_team')} vs {result.get('away_team')} on {result.get('date')}")
    else:
        print(f"  UUID {i}: invalid - {uid}")

print(f"\nResult: {found}/20 UUIDs were valid game fixtures")
