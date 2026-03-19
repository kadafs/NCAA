import os
import time
from playwright.sync_api import sync_playwright

print("\nBooting persistent Flashscore identity profile...")
profile_dir = os.path.join(os.getcwd(), 'playwright_profile')

with sync_playwright() as p:
    browser = p.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        headless=False,
        channel="chrome",
        args=['--disable-blink-features=AutomationControlled']
    )
    page = browser.new_page()
    page.goto('https://www.flashscore.com/basketball/', wait_until='domcontentloaded')
    
    print("\n=======================================================")
    print(" ACTION REQUIRED TO AUTHORIZE SCRAPER:")
    print(" 1. A physical Chrome window has just opened.")
    print(" 2. Please accept any Cookie banners if they appear.")
    print(" 3. If Flashscore presents an 'I am Human' box, check it.")
    print(" 4. Wait for the page to load successfully.")
    print(" 5. Simply close the Chrome window manually when finished.")
    print("=======================================================\n")
    print("Waiting for you to close the browser natively...")
    
    try:
        # The script will wait until the user manually closes the window
        page.wait_for_event("close", timeout=0)
    except Exception:
        pass
        
    print("\n[SUCCESS] Datadome Profile securely cached locally!")
    print("You may now run the primary scraper script, and it will inherit this trusted session.")
