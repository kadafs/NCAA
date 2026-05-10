from playwright.sync_api import sync_playwright
import re

def check_league_fixtures(league_slug):
    url = f"https://nbl1.com.au/competitions/{league_slug}/fixtures?tab=results"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print(f"[*] Loading {url}...")
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(5000)
            
            # Scroll down to load more?
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
        except Exception as e:
            print(f"[!] Error: {e}")
            
        html = page.content()
        fids = re.findall(r'data-fixture="([0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"', html.lower())
        print(f"Found {len(set(fids))} unique fixture IDs")
        
        # Check for May dates
        may_games = re.findall(r'may \d{1,2}, 2026', html.lower())
        print(f"Found {len(may_games)} games mentioned in May 2026")
        
        browser.close()

if __name__ == "__main__":
    check_league_fixtures("nbl1-north")
