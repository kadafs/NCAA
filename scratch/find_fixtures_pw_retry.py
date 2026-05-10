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
        print("[*] Loading fixtures page (long timeout)...")
        try:
            page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='domcontentloaded', timeout=60000)
            print("[*] DOM content loaded, waiting for network to settle...")
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"[!] Warning: {e}")
        
        html = page.content()
        print(f"[*] Page content length: {len(html)}")
        
        # Look for fixtureId in rendered HTML
        # The widget might use camelCase or different formats
        matches = re.findall(r'fixtureid[":= ]+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})', html.lower())
        print(f"Found {len(set(matches))} unique fixtureId matches")
        
        for m in sorted(list(set(matches))):
            parts = m.split('-')
            if parts[2].startswith('1'):
                print(f"  {m} (V1)")
            else:
                # print(f"  {m} (Not V1)")
                pass

        # Check for competition names
        comps = re.findall(r'competitionName":"([^"]+)"', html)
        if not comps:
            # Try a broader regex
            comps = re.findall(r'competition":"([^"]+)"', html)
            
        print(f"Found {len(set(comps))} unique competition names")
        for c in sorted(list(set(comps))):
            print(f"  {c}")
            
        browser.close()

if __name__ == "__main__":
    find_fixtures_playwright()
