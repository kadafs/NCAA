from playwright.sync_api import sync_playwright
import re
import json

def find_fixtures_playwright():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
        page = context.new_page()
        print("[*] Loading fixtures page...")
        page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='networkidle')
        
        # Give it some extra time to render the widget
        page.wait_for_timeout(5000)
        
        html = page.content()
        print(f"[*] Page content length: {len(html)}")
        
        # Look for fixtureId in rendered HTML
        matches = re.findall(r'fixtureId=([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', html.lower())
        print(f"Found {len(matches)} fixtureId matches (lowercase)")
        for m in set(matches):
            # Check if it starts with 1 in the 3rd group
            parts = m.split('-')
            if parts[2].startswith('1'):
                print(f"  {m} (V1)")
            else:
                print(f"  {m} (Not V1)")

        # Also look for competition names
        comps = re.findall(r'competitionName":"([^"]+)"', html)
        print(f"Found {len(set(comps))} unique competition names")
        for c in sorted(list(set(comps))):
            print(f"  {c}")
            
        browser.close()

if __name__ == "__main__":
    find_fixtures_playwright()
