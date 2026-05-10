from playwright.sync_api import sync_playwright
import re

def dump_fixtures_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
        )
        page = context.new_page()
        print("[*] Loading fixtures page...")
        try:
            page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='domcontentloaded', timeout=60000)
            page.wait_for_timeout(10000)
        except Exception as e:
            print(f"[!] Warning: {e}")
        
        html = page.content()
        with open('scratch/nbl1_dump.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[*] Dumped {len(html)} bytes to scratch/nbl1_dump.html")
            
        browser.close()

if __name__ == "__main__":
    dump_fixtures_html()
