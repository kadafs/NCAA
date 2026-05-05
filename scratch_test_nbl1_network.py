import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Intercept network to find the API
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        
        print("Navigating...")
        # Use domcontentloaded instead of networkidle to avoid timeout
        await page.goto('https://nbl1.com.au/games/24fed80e-d942-11f0-ae40-a990d4889692', wait_until="domcontentloaded")
        
        # Wait a fixed amount of time for scripts to fetch data
        print("Waiting 10 seconds for dynamic API calls...")
        await asyncio.sleep(10)
        
        print(f"\nCaptured {len(requests)} requests.")
        
        api_requests = []
        for r in requests:
            if any(kw in r.lower() for kw in ["api", "graphql", "json", "genius", "fiba", "stats", "boxscore"]):
                api_requests.append(r)
                
        print("\nFound Potential API Endpoints:")
        for r in set(api_requests):
            print(f" -> {r}")
            
        await browser.close()

asyncio.run(run())
