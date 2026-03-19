import sys
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    
    match_id = 'ENGhAxmL'
    url = f'https://www.flashscore.com/match/{match_id}/'
    print(f'Loading base URL: {url}')
    page.goto(url, wait_until='networkidle')
    page.wait_for_timeout(3000)
    
    try:
        page.click("button#onetrust-accept-btn-handler", timeout=2000)
    except: pass
    
    print("Looking for secondary STATS tab menu anchors...")
    try:
        # We search inside the secondary sub-menu tabs specifically!
        stats_tab = page.locator('a[href*="/summary/stats/"]')
        if stats_tab.is_visible():
            print("Found specific STATS href anchor! Clicking it...")
            stats_tab.click()
            page.wait_for_timeout(3000)
        else:
            print("Href anchor not visible, trying generic case-insensitive text click...")
            page.locator("text=STATS").nth(0).click()
            page.wait_for_timeout(3000)
    except Exception as e:
        print(f"Error executing click topology: {e}")
        
    page.screenshot(path='c:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/click_test_ENGhAxmL.png')
    
    rows = page.locator('.stat__row').all()
    print(f"\nSUCCESS: Physically extracted {len(rows)} Four-Factor stat rows!")
    for r in rows:
        if r.locator('.stat__categoryName').count() > 0:
            print(r.locator('.stat__categoryName').inner_text().strip())
    
    browser.close()
