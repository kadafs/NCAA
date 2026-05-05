import sys
import json
import re
from datetime import datetime
from playwright.sync_api import sync_playwright

COMPETITION_MAP = {
    "NBL1 South Men": 209, "NBL1 South Women": 210,
    "NBL1 North Men": 207, "NBL1 North Women": 208,
    "NBL1 East Men": 215, "NBL1 East Women": 216,
    "NBL1 Central Men": 212, "NBL1 Central Women": 211,
    "NBL1 West Men": 214, "NBL1 West Women": 213,
}

def parse_sportradar_date(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except ValueError:
        return None

def parse_minutes(mins_str):
    if not mins_str:
        return "00:00"
    m = re.search(r'PT(\d+)M', mins_str)
    s = re.search(r'(\d+)S$', mins_str)
    mm = m.group(1) if m else "0"
    ss = s.group(1) if s else "0"
    return f"{int(mm):02d}:{int(ss):02d}"

from scrape_nbl1 import _parse_box_score

confirmed_uuids = [
    "9169cd45-d6e8-11f0-a9c0-cfb7d5472bba",  # 2026-04-24
    "6af07794-d3dd-11f0-a3df-056d5acb892b",  # 2026-04-02
    "2422f919-da64-11f0-8a63-1f4631345f86",  # 2026-05-02
]

print("Testing CONFIRMED games with Playwright Context...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
    )
    
    print("Seeding NBL1 cookies...")
    page = context.new_page()
    page.goto("https://nbl1.com.au", timeout=60000)
    page.wait_for_timeout(3000)
    page.close()
    
    for uid in confirmed_uuids:
        print(f"\nChecking UUID {uid}")
        try:
            api_page = context.new_page()
            response = api_page.request.get(
                f"https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={uid}",
                headers={"Referer": "https://nbl1.com.au/"},
                timeout=15000
            )
            print(f"Status: {response.status}")
            data = response.json().get("data", {})
            api_page.close()
            
            box = _parse_box_score(data)
            if box:
                print(f"SUCCESS: {box['home_team']} vs {box['away_team']} ({box['date']}) [{box['competition']}]")
            else:
                print(f"FAILED TO EXTRACT (Box is None)")
                # Let's see why box is None
                fixture_top = data.get("fixture", {})
                print(f"  status: {fixture_top.get('status')}")
                print(f"  base: {bool(data.get('statistics', {}).get('data', {}).get('base', {}))}")
                
        except Exception as e:
            print(f"ERROR: {e}")
            
    browser.close()
