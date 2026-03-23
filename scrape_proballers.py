import sys
import os
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

try:
    from playwright_stealth import Stealth
    HAS_STEALTH = True
except ImportError:
    print("Warning: playwright_stealth not installed. Cloudflare may block execution.")
    HAS_STEALTH = False

def parse_boxscore(html):
    """
    Parses the raw Proballers Box Score HTML and mathematical extracts the Four Factors.
    Returns: {"home": {...}, "away": {...}}
    """
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all('table')
    
    # Proballers tables:
    # [0] -> Quarter scores
    # [1] -> Home Team Stats
    # [2] -> Away Team Stats
    
    if len(tables) < 3:
        return None
        
    def extract_team_totals(table):
        rows = table.find_all('tr')
        if len(rows) < 2: return None
        
        # The last row in a Proballers stats table embodies the composite team totals
        totals_row = rows[-1]
        cells = [td.text.strip() for td in totals_row.find_all('td')]
        
        if len(cells) < 18: return None
        
        # Parse Field Goals (e.g. "27-44")
        twos = cells[5].split('-')
        threes = cells[6].split('-')
        fga = int(twos[1]) + int(threes[1]) if len(twos)==2 and len(threes)==2 else 0
        
        # Parse Free Throws (e.g. "24-29")
        fts = cells[8].split('-')
        fta = int(fts[1]) if len(fts)==2 else 0
        
        return {
            "team_name": cells[0],
            "points": int(cells[1] or 0),
            "FGA": fga,
            "FTA": fta,
            "ORB": int(cells[10] or 0),
            "DRB": int(cells[11] or 0),
            "TRB": int(cells[12] or 0),
            "AST": int(cells[13] or 0),
            "TOV": int(cells[14] or 0),
            "STL": int(cells[15] or 0),
            "BLK": int(cells[16] or 0)
        }
        
    # Extract Title for Match Date (e.g. Washington Wizards vs. Toronto Raptors - Oct 12, 2025 - Game recap | Proballers)
    title = soup.find('title').text if soup.find('title') else ""
    date_str = title.split(' - ')[1] if ' - ' in title else "Unknown"
    
    h_data = extract_team_totals(tables[1])
    a_data = extract_team_totals(tables[2])
    
    if not h_data or not a_data:
        return None
        
    return {
        "date": date_str,
        "home_team": h_data["team_name"],
        "away_team": a_data["team_name"],
        "home_score": h_data["points"],
        "away_score": a_data["points"],
        "stats": {
            "home": h_data,
            "away": a_data
        }
    }
def extract_league_schedule(url, context):
    """
    Extracts all box score URLs from a parent Proballers League/Team Schedule page.
    """
    page = context.new_page()
    if HAS_STEALTH: Stealth().apply_stealth_sync(page)
    
    # Random sleep to avoid 520 errors
    time.sleep(2)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        page.wait_for_timeout(4000)
    except Exception as e:
        print(f"  -> Cloudflare telemetry timeout bypassed natively.")
        
    links = page.locator('a').all()
    box_urls = []
    
    for l in links:
        href = l.get_attribute('href')
        if href and '/basketball/game/' in href:
            full_url = "https://www.proballers.com" + href if not href.startswith("http") else href
            if full_url not in box_urls:
                box_urls.append(full_url)
                
    page.close()
    
    # Reverse to prioritize the most recent games (found at the bottom of the schedule)
    box_urls.reverse()
    return box_urls

def scrape_match(url, context):
    page = context.new_page()
    if HAS_STEALTH: Stealth().apply_stealth_sync(page)
    
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
    except:
        pass # Catch infinite Cloudflare spinner loading loops
        
    try:
        html = page.content()
        data = parse_boxscore(html)
    except Exception as e:
        print(f"      [!] Skipping game (DOM locked/navigating): {e}")
        data = {}
        
    page.close()
    return data

import argparse
import random

def run_proballers_scraper(target_url, max_games=None, cutoff_date=None):
    domain_slug = target_url.strip('/').split('/')[-2]
    out_file = f"data/historical/proballers_{domain_slug}.json"
    
    existing_data = []
    seen_sigs = set()
    
    # Intelligent resume logic: Load existing data to append strictly new games
    if os.path.exists(out_file) and os.path.getsize(out_file) > 1024:
        try:
            with open(out_file, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                for item in existing_data:
                    sig = f"{item.get('date')} {item.get('home_team')} {item.get('away_team')}"
                    seen_sigs.add(sig)
            print(f"  [~] Loaded {len(existing_data)} existing historical records.")
        except Exception as e:
            print(f"  [!] Failed to load existing payload: {str(e)}. Starting fresh.")

    print(f"\n===========================================================")
    print(f"  STARTING PROBALLERS SCRAPER -> {domain_slug.upper()}")
    print(f"===========================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        matches = extract_league_schedule(target_url, context)
        print(f"  -> Extracted {len(matches)} historical payload links from DOM.")
        
        if max_games and len(matches) > max_games:
            matches = matches[:max_games]
            
        new_matches_added = 0
        for i, match_url in enumerate(matches):
            print(f"      [{i+1}/{len(matches)}] Harvesting advanced stats: {match_url.split('/')[-1]}")
            m_data = scrape_match(match_url, context)
            if m_data:
                game_date_str = m_data.get('date', 'Unknown')
                if cutoff_date and game_date_str != "Unknown":
                    try:
                        game_dt = datetime.strptime(game_date_str.strip(), "%b %d, %Y").date()
                        cutoff_dt = datetime.strptime(cutoff_date, "%Y-%m-%d").date()
                        if game_dt < cutoff_dt:
                            print(f"        -> [!] Game date {game_date_str} is older than cutoff {cutoff_date}. Stopping extraction.")
                            break
                    except Exception as e:
                        pass # Silently continue if date parsing fails

                sig = f"{m_data.get('date')} {m_data.get('home_team')} {m_data.get('away_team')}"
                if sig not in seen_sigs:
                    existing_data.append(m_data)
                    seen_sigs.add(sig)
                    new_matches_added += 1
                    print(f"        -> [+] Appended new data!")
                else:
                    print(f"        -> [~] Match already exists in dataset: {sig}")
                
            # Intelligent rate limit to avoid Cloudflare shadowbans
            time.sleep(random.uniform(2.1, 4.3))
                
        print(f"\n  [+] Mapped Mathematical Payloads (New: {new_matches_added})")
        
        if existing_data:
            os.makedirs("data/historical", exist_ok=True)
            with open(out_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=2, ensure_ascii=False)
            print(f"  [+] SUCCESS: Historical [ADVANCED] payload locked -> {out_file}")
            
        browser.close()
        return True

def get_daily_urls(date_str):
    """
    Reads the daily fixtures JSON to find which leagues are actively playing,
    then looks up their proballers_url. Only active leagues will be scraped.
    """
    if date_str == "today" or not date_str:
        from datetime import timezone
        ET_TZ = timezone.utc
        date_str = datetime.now(ET_TZ).strftime("%Y-%m-%d")
        
    fixtures_file = f"data/api_basketball_today_{date_str}.json"
    
    if not os.path.exists(fixtures_file):
        print(f"  [!] Fixtures file not found: {fixtures_file}")
        print(f"      Attempting to fetch fixtures for {date_str}...")
        try:
            # Reuses the exact fetcher logic from the daily runner
            from run_basketball_daily import fetch_today_fixtures
            fetch_today_fixtures(date_str)
        except Exception as e:
            print(f"  [X] Failed to fetch fixtures: {e}")
            return []
            
    if not os.path.exists(fixtures_file):
        return []
        
    try:
        with open(fixtures_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        try:
            from run_basketball_daily import EXCLUDED_LEAGUE_IDS, EXCLUDED_LEAGUE_NAMES
        except ImportError:
            EXCLUDED_LEAGUE_IDS = set()
            EXCLUDED_LEAGUE_NAMES = set()
            
        valid_leagues = [
            l for l in data.get("leagues_summary", [])
            if l.get("league_id") not in EXCLUDED_LEAGUE_IDS
            and l.get("league_name") not in EXCLUDED_LEAGUE_NAMES
            and str(l.get("country") or "").strip().upper() != "USA"
        ]
        
        leagues_today = [str(l.get("league_id")) for l in valid_leagues if l.get("league_id")]
        
        urls = []
        for lid in leagues_today:
            cfg_path = f"configs/leagues/{lid}.json"
            if os.path.exists(cfg_path):
                try:
                    with open(cfg_path, "r", encoding="utf-8") as cf:
                        cfg = json.load(cf)
                        url = cfg.get("proballers_url")
                        if url:
                            if url not in urls:
                                urls.append(url)
                except Exception:
                    pass
        # 2. Legacy Method: Lookup via league_slug_map + proballers_schedule_links
        map_file = "data/league_slug_map.json"
        txt_files = ["proballers_schedule_links.txt", "proballers_priority_links.txt"]
        
        if os.path.exists(map_file):
            try:
                with open(map_file, "r", encoding="utf-8") as mf:
                    slug_map = json.load(mf)
                    
                for tfile in txt_files:
                    if os.path.exists(tfile):
                        with open(tfile, "r", encoding="utf-8") as tf:
                            for line in tf:
                                url = line.strip()
                                if not url or url.startswith("#"): continue
                                
                                parts = url.strip("/").split("/")
                                if len(parts) >= 2:
                                    slug = parts[-2]
                                    api_id = slug_map.get(slug)
                                    if not api_id:
                                        api_id = slug_map.get(slug.replace("-", "_"))
                                        
                                    if api_id and str(api_id) in leagues_today:
                                        if url not in urls:
                                            urls.append(url)
            except Exception as e:
                print(f"  [X] Failed parsing legacy mapping: {e}")

        return urls
    except Exception as e:
        print(f"  [X] Error parsing daily leagues: {e}")
        return []

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Proballers Advanced Metrics Mass Scraper")
    parser.add_argument("--url", type=str, help="Single schedule URL to scrape")
    parser.add_argument("--file", type=str, help="Text file containing multiple schedule URLs to batch process")
    parser.add_argument("--daily", type=str, nargs="?", const="today", help="Scrape only leagues playing on this date (YYYY-MM-DD or 'today')")
    parser.add_argument("--max", type=int, default=200, help="Max games to scrape per league (prevent timeout during sync)")
    parser.add_argument("--cutoff_date", type=str, help="Do not scrape games older than this date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    target_urls = []
    
    if args.daily:
        print(f"\n[DAILY OPTIMIZATION] Identifying active leagues for date: {args.daily}")
        target_urls = get_daily_urls(args.daily)
        print(f"-> Found {len(target_urls)} active Proballers leagues scheduled for {args.daily if args.daily != 'today' else 'today'}\n")
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File {args.file} not found.")
            sys.exit(1)
        with open(args.file, "r") as f:
            target_urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        print(f"Found {len(target_urls)} leagues in target manifest. Commencing Mass Extraction Sequence.")
    elif args.url:
        target_urls = [args.url]
    else:
        parser.print_help()
        sys.exit(0)
        
    for idx, url in enumerate(target_urls):
        print(f"\n[BATCH ROUTINE] Extracting League {idx+1} of {len(target_urls)}: {url.split('/')[-2] if '/' in url else url}")
        run_proballers_scraper(url, max_games=args.max, cutoff_date=args.cutoff_date)
        
        if idx < len(target_urls) - 1:
            cooldown = random.uniform(8.5, 14.5)
            print(f"  -> Cooldown for {cooldown:.1f}s before next league...")
            time.sleep(cooldown)
