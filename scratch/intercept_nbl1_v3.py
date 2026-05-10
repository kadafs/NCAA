from playwright.sync_api import sync_playwright

def intercept_nbl1():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        requests_found = []
        page.on("request", lambda request: requests_found.append(request.url))
        
        print("[*] Loading NBL1 fixtures (long wait + scroll)...")
        try:
            page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='domcontentloaded', timeout=60000)
            print("[*] Page loaded, waiting 20s and scrolling...")
            for _ in range(5):
                page.evaluate("window.scrollBy(0, 500)")
                page.wait_for_timeout(4000)
        except Exception as e:
            print(f"[!] Warning: {e}")
        
        print(f"[*] Total requests: {len(requests_found)}")
        sportradar_urls = [u for u in requests_found if "sportradar" in u]
        print(f"[*] Found {len(sportradar_urls)} Sportradar requests")
        for url in sorted(list(set(sportradar_urls))):
            print(f"  {url}")
                
        browser.close()

if __name__ == "__main__":
    intercept_nbl1()
