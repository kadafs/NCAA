import sys
import os
import json
import time
from playwright.sync_api import sync_playwright

def scrape_one_league(url, browser):
    print(f"\n===========================================================")
    print(f"  STARTING FLASHSCORE SCRAPER: {url}")
    print(f"===========================================================")
    
    parts = [p for p in url.split("/") if p and p != "basketball"]
    slug = "custom_league"
    if len(parts) >= 2:
        slug = f"{parts[-2]}_{parts[-1]}"
        if slug.endswith("_results"):
            slug = f"{parts[-3]}_{parts[-2]}"
            
    slug = slug.replace("-", "_").replace(".", "")
    out_file = f"data/historical/flashscore_{slug}.json"
    
    if os.path.exists(out_file) and "--force" not in sys.argv:
        print(f"  -> SKIP: {out_file} already exists. (Use --force to overwrite)")
        return True

    page = browser.new_page()
    print("  -> Loading Flashscore Results layer...")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=15000)
    except Exception as e:
        print(f"  -> ERROR loading page: {e}")
        page.close()
        return False
    
    try:
        page.click("button#onetrust-accept-btn-handler", timeout=2000)
        print("  -> Bypassed cookie overlay.")
    except:
        pass
        
    print("  -> Rapidly expanding hidden matches...")
    expansions = 0
    while True:
        try:
            more_link = page.locator("a.event__more.event__more--static")
            if more_link.is_visible(timeout=1500):
                more_link.click()
                expansions += 1
                time.sleep(0.5)
            else:
                break
        except Exception:
            break
            
    print(f"  -> Finished expanding {expansions} pagination blocks.")
    print("  -> Harvesting JSON box scores and Base IDs...")
    games = []
    
    match_elements = page.locator("div.event__match").all()
    for element in match_elements:
        try:
            match_id = element.get_attribute("id")
            if match_id and match_id.startswith("g_3_"):
                match_id = match_id[4:]
            else:
                match_id = None

            time_str = element.locator(".event__time").inner_text().strip() if element.locator(".event__time").count() > 0 else ""
            home = element.locator(".event__participant--home").inner_text().strip()
            away = element.locator(".event__participant--away").inner_text().strip()
            
            home_score_el = element.locator(".event__score--home")
            away_score_el = element.locator(".event__score--away")
            
            if home_score_el.count() == 0 or away_score_el.count() == 0:
                continue
                
            home_score = home_score_el.inner_text().strip()
            away_score = away_score_el.inner_text().strip()
            
            if not home_score.isdigit() or not away_score.isdigit():
                continue

            games.append({
                "match_id": match_id,
                "date": time_str,
                "home_team": home,
                "away_team": away,
                "home_score": int(home_score),
                "away_score": int(away_score),
                "advanced_stats": {}
            })
        except Exception:
            pass
            
    if len(games) == 0:
        print("  -> ERROR: 0 valid games found. The URL might be a broken API-slug translation (404 Page).")
        page.close()
        return False
        
    print(f"  -> Natively extracted {len(games)} basic box scores.")
    
    if "--fast" not in sys.argv:
        print(f"  -> Initiating DEEP SCRAPE. Harvesting Advanced Four-Factor Stats mapping...")
        for i, g in enumerate(games):
            if not g["match_id"]: continue
            
            stats_url = f"https://www.flashscore.com/match/{g['match_id']}/#/match-summary/match-statistics/0"
            try:
                page.goto(stats_url, wait_until="domcontentloaded", timeout=6000)
                
                # Dynamically wait for the React stats table to finish painting
                try:
                    page.wait_for_selector(".stat__row", state="attached", timeout=3500)
                except Exception:
                    pass # If it times out here, the match genuinely doesn't have advanced stats published
                
                rows = page.locator(".stat__row").all()
                stats_obj = {}
                for r in rows:
                    if r.locator(".stat__categoryName").count() > 0:
                        c = r.locator(".stat__categoryName").inner_text().strip().lower()
                        h = r.locator(".stat__homeValue").inner_text().strip() if r.locator(".stat__homeValue").count() > 0 else None
                        a = r.locator(".stat__awayValue").inner_text().strip() if r.locator(".stat__awayValue").count() > 0 else None
                        if h and a:
                            stats_obj[c] = {"home": h, "away": a}
                            
                g["advanced_stats"] = stats_obj
                print(f"      [{i+1}/{len(games)}] Deep Profile: {g['home_team']} vs {g['away_team']} -> Found {len(stats_obj)} physical metrics")
            except Exception as e:
                print(f"      [{i+1}/{len(games)}] Deep Profile: Timeout/Missing DOM on {g['match_id']}")
    else:
        print("  -> [--fast] flag detected. Bypassing Deep Scrape.")

    page.close()
    
    os.makedirs("data/historical", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump({"source_url": url, "total_games": len(games), "games": games}, f, indent=2)
        
    print(f"  -> Successfully packaged Advanced Dataset into: {out_file}\n")
    return True


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        if os.path.exists("batch_failed_urls.txt"):
            print("Usage: python scrape_flashscore.py <url1> [url2]...")
            print("       python scrape_flashscore.py $(cat batch_failed_urls.txt)")
            print("\nOptions:")
            print("  --fast    Skip advanced statistics (Rebounds, Turnovers) to run 10x faster.")
            print("  --force   Overwrite existing JSON files locally.")
        else:
            print("Usage: python scrape_flashscore.py <url1> [url2] [url3] ...")
        sys.exit(1)
        
    print(f"Initializing central Playwright pipeline to sequentially scrape {len(args)} leagues...")
    
    successful = []
    failed = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in args:
            try:
                if scrape_one_league(url, browser):
                    successful.append(url)
                else:
                    failed.append(url)
            except Exception as e:
                print(f"  -> CRITICAL FAILURE ON LEAGUE: {url} | Error: {e}")
                failed.append(url)
        browser.close()
        
    print(f"\n===========================================================")
    print("  SCRAPING BATCH COMPLETE")
    print(f"  Successfully extracted:   {len(successful)} leagues")
    print(f"  Failed (404/Broken URL):  {len(failed)} leagues")
    print(f"===========================================================")
    
    if failed:
        with open("batch_failed_urls.txt", "w") as f:
            for u in failed:
                f.write(u + "\n")
        print("\n[!] IMPORTANT:")
        print("All broken URLs have been safely isolated and saved to -> 'batch_failed_urls.txt'")
        print("You can manually correct the spelling in that file, and then simply re-run those specific failures.")
    else:
        print("\nAll URLs translated and processed perfectly!")

if __name__ == "__main__":
    main()
