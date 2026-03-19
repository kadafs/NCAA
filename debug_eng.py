import os
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    profile_dir = os.path.join(os.getcwd(), 'playwright_profile')
    context = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        channel="chrome",
        args=['--disable-blink-features=AutomationControlled']
    )
    page = context.new_page()
    match_id = 'ENGhAxmL'
    url = f"https://www.flashscore.com/match/{match_id}/"
    print(f"Loading base SPA URL: {url}")
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=12000)
    except Exception as e:
        # Ignore Ads blocking the network port from reaching active 'load' state
        pass
        
    page.wait_for_timeout(2000)
    print("Beginning DOM Extraction...")
    
    try:
        # Strategy 1: Anchor explicitly pointing to new nested stats container
        stats_tab = page.locator('a[href*="/summary/stats/"]')
        if stats_tab.count() > 0:
            print(" -> Found nested React anchor (/summary/stats/)")
            stats_tab.first.click(timeout=3000)
        else:
            print(" -> Trying heuristic text-match...")
            page.locator('text="STATS"').first.click(timeout=3000)
    except Exception as e:
        print(f" -> ERROR clicking DOM component: {e}")
        
    page.wait_for_timeout(2000)
    
    rows = page.locator(".stat__row").all()
    print(f"\n[FINAL TARGET] Extracted {len(rows)} Four-Factor Statistical Arrays!")
    for r in rows:
        if r.locator(".stat__categoryName").count() > 0:
            print(" - " + r.locator(".stat__categoryName").inner_text().strip())
            
    context.close()
