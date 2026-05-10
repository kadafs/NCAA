from playwright.sync_api import sync_playwright
import re

def scroll_and_find():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("[*] Loading fixtures page...")
        page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='domcontentloaded')
        page.wait_for_timeout(5000)
        
        print("[*] Scrolling 10 times...")
        for i in range(10):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
            
        html = page.content()
        fids = re.findall(r'data-fixture="([0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"', html.lower())
        print(f"Found {len(set(fids))} unique fixture IDs after scrolling")
        
        # Check for May dates
        may_games = re.findall(r'may \d{1,2}, 2026', html.lower())
        print(f"Found {len(may_games)} May games")
        
        browser.close()

if __name__ == "__main__":
    scroll_and_find()
