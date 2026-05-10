from playwright.sync_api import sync_playwright
import re

def check_league(slug):
    url = f"https://nbl1.com.au/competitions/{slug}/fixtures?tab=results"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"[*] Loading {url}...")
        page.goto(url, wait_until='domcontentloaded')
        page.wait_for_timeout(10000)
        html = page.content()
        fids = re.findall(r'data-fixture="([0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"', html.lower())
        print(f"Found {len(set(fids))} fixture IDs")
        
        # Check for May dates
        may_games = re.findall(r'may \d{1,2}, 2026', html.lower())
        print(f"Found {len(may_games)} May games")
        
        if may_games:
            print("SAMPLE MAY DATES FOUND!")
            
        browser.close()

if __name__ == "__main__":
    check_league("nbl1-north")
    check_league("nbl1-south")
    check_league("nbl1-west")
