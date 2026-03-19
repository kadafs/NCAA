import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    # Mask native headless browser identity
    page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    url = 'https://www.flashscore.com/match/0lpLhDEl/#/match-summary/match-statistics/0'
    print(f'Loading {url} with JS cloaking...')
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(4000)
    
    try:
        page.wait_for_selector('.stat__row', state='attached', timeout=5000)
        rows = page.locator('.stat__row').all()
        print(f'\nSUCCESS: Found {len(rows)} advanced stat rows using native JS cloaking!')
        for r in rows:
            if r.locator('.stat__categoryName').count() > 0:
                print(r.locator('.stat__categoryName').inner_text().strip())
    except Exception as e:
        print(f'\nFAILED: Datadome still aggressively blocked the payload. {e}')
        
    browser.close()
