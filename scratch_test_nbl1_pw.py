import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("Navigating...")
        await page.goto('https://nbl1.com.au/games/24fed80e-d942-11f0-ae40-a990d4889692')
        print("Waiting for Box Score tab...")
        
        # NBL1 uses Webflow and potentially genius sports iframe or div.
        # Let's wait for network idle to ensure data loads
        await page.wait_for_load_state('networkidle', timeout=15000)
        
        # Check if there are iframes
        frames = page.frames
        print(f"Frames: {len(frames)}")
        
        # Look for table or specific text
        content = await page.content()
        if "Maddy Hinton" in content:
            print("FOUND Maddy Hinton in main page content!")
        else:
            print("NOT FOUND in main page content.")
            for i, f in enumerate(frames):
                try:
                    f_content = await f.content()
                    if "Maddy Hinton" in f_content:
                        print(f"FOUND in frame {i} ({f.url})!")
                except:
                    pass
        await browser.close()

asyncio.run(run())
