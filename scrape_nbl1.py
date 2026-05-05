"""
scrape_nbl1.py
==============
Scrapes NBL1 (Australia) box scores using the Sportradar API that powers nbl1.com.au.
Captures team stats AND player-level stats needed for SDI calculation.
Automatically routes fixtures to the correct league file based on Competition Name.

Usage:
    python scrape_nbl1.py
    python scrape_nbl1.py --cutoff_date 2025-10-01

NBL1 League IDs (API-Basketball):
    209 = NBL1 South Men         210 = NBL1 South Women
    207 = NBL1 North Men         208 = NBL1 North Women
    215 = NBL1 East Men          216 = NBL1 East Women
    212 = NBL1 Central Men       211 = NBL1 Central Women
    214 = NBL1 West Men          213 = NBL1 West Women
"""

import os
import json
import re
import sys
import time
import argparse
import requests
import random
from datetime import datetime

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"

# Map Sportradar Competition Names to API-Basketball League IDs
COMPETITION_MAP = {
    "NBL1 South Men": 209,
    "NBL1 South Women": 210,
    "NBL1 North Men": 207,
    "NBL1 North Women": 208,
    "NBL1 East Men": 215,
    "NBL1 East Women": 216,
    "NBL1 Central Men": 212,
    "NBL1 Central Women": 211,
    "NBL1 West Men": 214,
    "NBL1 West Women": 213,
}

def parse_sportradar_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str.replace("Z", "+00:00")).strftime("%b %d, %Y")
    except Exception:
        return None

def parse_minutes(pt_str):
    if not pt_str:
        return "0:00"
    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", pt_str)
    if not match:
        return "0:00"
    h = int(match.group(1) or 0)
    m = int(match.group(2) or 0) + h * 60
    s = int(match.group(3) or 0)
    return f"{m}:{s:02d}"

def extract_box_score(fixture_id):
    url = SPORTRADAR_URL.format(fixture_id)
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return None
        data = res.json().get("data", {})
    except Exception:
        return None

    banner = data.get("banner", {})
    fixture_meta = banner.get("fixture", {})
    competition = banner.get("competition", {})
    competitors = fixture_meta.get("competitors", [])

    if not competition or not competition.get("name"):
        return None

    comp_name = competition.get("name")
    if comp_name not in COMPETITION_MAP:
        return None

    home_team, away_team = None, None
    for c in competitors:
        if c.get("isHome"):
            home_team = c.get("name", c.get("code", "Unknown"))
        else:
            away_team = c.get("name", c.get("code", "Unknown"))

    if not home_team or not away_team:
        return None

    # Date is in the TOP-LEVEL fixture object, not banner.fixture
    fixture_top = data.get("fixture", {})
    status = fixture_top.get("status", "").upper()
    
    # Only process games that have actually been played
    # CONFIRMED = completed, CLOSED = final, PLAYED = done
    # Skip SCHEDULED, NOTSTARTED, POSTPONED, CANCELLED
    completed_statuses = {"CONFIRMED", "CLOSED", "PLAYED", "ENDED", "FINAL", "FT", "AOT"}
    if status not in completed_statuses:
        return None

    date_str = fixture_top.get("startTimeLocal") or fixture_top.get("startTimeUTC")
    game_date = parse_sportradar_date(date_str)
    if not game_date:
        return None

    home_score, away_score = None, None
    for side in data.get("summary", {}).get("competitors", []):
        if side.get("isHome"):
            home_score = side.get("score")
        else:
            away_score = side.get("score")

    stats_base = data.get("statistics", {}).get("data", {}).get("base", {})
    if not stats_base:
        return None

    def get_players(side_data):
        players = []
        for group in side_data.get("persons", []):
            for row in group.get("rows", []):
                s = row.get("statistics", {})
                mins = s.get("minutes", "")
                if not mins or not row.get("participated", True):
                    continue
                players.append({
                    "name":  row.get("personName", "Unknown"),
                    "pts":   s.get("points", 0),
                    "reb":   s.get("rebounds", 0),
                    "orb":   s.get("reboundsOffensive", 0),
                    "drb":   s.get("reboundsDefensive", 0),
                    "ast":   s.get("assists", 0),
                    "stl":   s.get("steals", 0),
                    "blk":   s.get("blocks", 0),
                    "tov":   s.get("turnovers", 0),
                    "fgm":   s.get("fieldGoalsMade", 0),
                    "fga":   s.get("fieldGoalsAttempted", 0),
                    "ftm":   s.get("freeThrowsMade", 0),
                    "fta":   s.get("freeThrowsAttempted", 0),
                    "3pm":   s.get("pointsThreeMade", 0),
                    "3pa":   s.get("pointsThreeAttempted", 0),
                    "pf":    s.get("foulsTotal", 0),
                    "min":   parse_minutes(mins),
                })
        return players

    def get_totals(entity):
        return {
            "pts": entity.get("points", 0),
            "fgm": entity.get("fieldGoalsMade", 0),
            "fga": entity.get("fieldGoalsAttempted", 0),
            "ftm": entity.get("freeThrowsMade", 0),
            "fta": entity.get("freeThrowsAttempted", 0),
            "3pm": entity.get("pointsThreeMade", 0),
            "3pa": entity.get("pointsThreeAttempted", 0),
            "reb": entity.get("rebounds", 0),
            "orb": entity.get("reboundsOffensive", 0),
            "drb": entity.get("reboundsDefensive", 0),
            "ast": entity.get("assists", 0),
            "stl": entity.get("steals", 0),
            "blk": entity.get("blocks", 0),
            "tov": entity.get("turnovers", 0),
        }

    home_data = stats_base.get("home", {})
    away_data = stats_base.get("away", {})
    home_players = get_players(home_data)
    away_players = get_players(away_data)

    if home_score is None:
        home_score = home_data.get("entity", {}).get("points", 0)
    if away_score is None:
        away_score = away_data.get("entity", {}).get("points", 0)

    if not home_players or not away_players:
        return None

    return {
        "date":       game_date,
        "home_team":  home_team,
        "away_team":  away_team,
        "home_score": home_score,
        "away_score": away_score,
        "competition": comp_name,
        "league_id":  COMPETITION_MAP[comp_name],
        "fixture_id": fixture_id,
        "stats": {
            "home": {**get_totals(home_data.get("entity", {})), "players": home_players},
            "away": {**get_totals(away_data.get("entity", {})), "players": away_players},
        }
    }


def load_existing_data(league_id):
    out_file = f"data/historical/nbl1_official_{league_id}.json"
    existing_data, seen_sigs = [], set()
    if os.path.exists(out_file) and os.path.getsize(out_file) > 100:
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw:
                if item.get("stats", {}).get("home", {}).get("players"):
                    sig = f"{item.get('date')} {item.get('home_team')} {item.get('away_team')}"
                    seen_sigs.add(sig)
                    existing_data.append(item)
        except Exception:
            pass
    return existing_data, seen_sigs


def run_nbl1_scraper(cutoff_date=None):
    print("\n===========================================================", flush=True)
    print("  NBL1 CENTRALIZED SCRAPER (Sportradar API)", flush=True)
    print("===========================================================", flush=True)
    print("  [+] Launching Playwright browser (required for Sportradar API)...", flush=True)

    from playwright.sync_api import sync_playwright

    cutoff_dt = datetime.strptime(cutoff_date, "%Y-%m-%d").date() if cutoff_date else None

    # Load Bad ID Cache
    invalid_cache_file = "data/historical/nbl1_invalid_uuids.json"
    invalid_uuids = set()
    if os.path.exists(invalid_cache_file):
        try:
            invalid_uuids = set(json.load(open(invalid_cache_file, "r", encoding="utf-8")))
            print(f"  [+] Loaded {len(invalid_uuids)} known invalid UUIDs from cache.", flush=True)
        except Exception:
            pass

    # Pre-load all existing league data
    league_datasets = {}
    league_sigs = {}
    for c_name, l_id in COMPETITION_MAP.items():
        data, sigs = load_existing_data(l_id)
        league_datasets[l_id] = data
        league_sigs[l_id] = sigs

    new_count = 0

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
            )

            # ---- Step 1: Load NBL1 fixtures page to get UUIDs + set session cookies ----
            print("  [+] Loading NBL1 fixtures page to seed session cookies...", flush=True)
            raw_uuids = set()
            for attempt in range(1, 4):
                page = context.new_page()
                page.goto("https://nbl1.com.au/fixtures?tab=results", wait_until='domcontentloaded', timeout=60000)
                try:
                    page.wait_for_load_state('networkidle', timeout=25000)
                except Exception:
                    pass
                page.wait_for_timeout(3000)
                html_content = page.content()
                page.close()

                found = set(re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', html_content.lower()))
                print(f"  [*] Attempt {attempt}: Extracted {len(found)} UUIDs.", flush=True)

                if len(found) >= 500:
                    raw_uuids = found
                    break
                elif attempt < 3:
                    print(f"  [!] Too few UUIDs - Rosetta may not have loaded. Retrying...", flush=True)
                else:
                    print(f"  [!] Warning: Only {len(found)} UUIDs after 3 attempts. Proceeding anyway.", flush=True)
                    raw_uuids = found

            print(f"  [+] Final UUID count: {len(raw_uuids)}", flush=True)
            print(f"  [+] Loaded existing data. Beginning UUID processing...\n", flush=True)

            # ---- Step 2: Use the SAME browser context to call Sportradar API ----
            # This carries the session cookies and proper headers, bypassing blocks.
            SPORTRADAR_URL = "https://embed-api.eui.connect.sportradar.com/v1/embed/3/fixture_detail?fixtureId={}"
            total_uuids = len(raw_uuids)

            for i, fid in enumerate(raw_uuids):
                if i % 10 == 0:
                    print(f"  [*] Checking UUID {i}/{total_uuids}...", flush=True)

                if fid in invalid_uuids:
                    continue

                try:
                    api_page = context.new_page()
                    response = api_page.request.get(
                        SPORTRADAR_URL.format(fid),
                        headers={"Referer": "https://nbl1.com.au/"},
                        timeout=15000
                    )
                    api_page.close()

                    if response.status != 200:
                        invalid_uuids.add(fid)
                        continue

                    data = response.json().get("data", {})
                    box = _parse_box_score(data)
                    if not box:
                        invalid_uuids.add(fid)
                        continue

                except Exception:
                    invalid_uuids.add(fid)
                    continue

                l_id = box["league_id"]

                if cutoff_dt and box.get("date"):
                    try:
                        gdt = datetime.strptime(box["date"], "%b %d, %Y").date()
                        if gdt < cutoff_dt:
                            continue
                    except Exception:
                        pass

                sig = f"{box['date']} {box['home_team']} {box['away_team']}"
                if sig in league_sigs[l_id]:
                    continue

                league_datasets[l_id].append(box)
                league_sigs[l_id].add(sig)
                new_count += 1
                print(f"  [+] {box['competition']}: {box['home_team']} vs {box['away_team']} ({box['date']})", flush=True)

                os.makedirs("data/historical", exist_ok=True)
                out_file = f"data/historical/nbl1_official_{l_id}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(league_datasets[l_id], f, indent=2, ensure_ascii=False)

            browser.close()

    except Exception as e:
        print(f"  [!] Playwright error: {e}")

    # Save updated Bad ID Cache
    try:
        with open(invalid_cache_file, "w", encoding="utf-8") as f:
            json.dump(list(invalid_uuids), f)
    except Exception as e:
        print(f"  [!] Failed to save Bad ID Cache: {e}")

    print(f"\n  [+] Total new NBL1 games added: {new_count}")
    print("===========================================================\n")


def _parse_box_score(data):
    """Parse Sportradar API response dict into a game record. Separated from
    extract_box_score so it can be used by the Playwright-context caller."""
    banner = data.get("banner", {})
    fixture_meta = banner.get("fixture", {})
    competition = banner.get("competition", {})
    competitors = fixture_meta.get("competitors", [])

    if not competition or not competition.get("name"):
        return None

    comp_name = competition.get("name")
    if comp_name not in COMPETITION_MAP:
        return None

    home_team = next((c.get("name", c.get("code", "Unknown")) for c in competitors if c.get("isHome")), None)
    away_team = next((c.get("name", c.get("code", "Unknown")) for c in competitors if not c.get("isHome")), None)
    if not home_team or not away_team:
        return None

    fixture_top = data.get("fixture", {})
    status = fixture_top.get("status", "").upper()
    completed_statuses = {"CONFIRMED", "CLOSED", "PLAYED", "ENDED", "FINAL", "FT", "AOT"}
    if status not in completed_statuses:
        return None

    date_str = fixture_top.get("startTimeLocal") or fixture_top.get("startTimeUTC")
    game_date = parse_sportradar_date(date_str)
    if not game_date:
        return None

    home_score, away_score = None, None
    for side in data.get("summary", {}).get("competitors", []):
        if side.get("isHome"):
            home_score = side.get("score")
        else:
            away_score = side.get("score")

    stats_base = data.get("statistics", {}).get("data", {}).get("base", {})
    if not stats_base:
        return None

    def get_players(side_data):
        players = []
        for group in side_data.get("persons", []):
            for row in group.get("rows", []):
                if not row.get("participated", False):
                    continue
                s = row.get("statistics", {})
                mins = s.get("minutes", "")
                if not mins:
                    continue
                players.append({
                    "name":  row.get("personName", "Unknown"),
                    "pts":   s.get("points", 0),
                    "reb":   s.get("rebounds", 0),
                    "orb":   s.get("reboundsOffensive", 0),
                    "drb":   s.get("reboundsDefensive", 0),
                    "ast":   s.get("assists", 0),
                    "stl":   s.get("steals", 0),
                    "blk":   s.get("blocks", 0),
                    "tov":   s.get("turnovers", 0),
                    "fgm":   s.get("fieldGoalsMade", 0),
                    "fga":   s.get("fieldGoalsAttempted", 0),
                    "ftm":   s.get("freeThrowsMade", 0),
                    "fta":   s.get("freeThrowsAttempted", 0),
                    "3pm":   s.get("pointsThreeMade", 0),
                    "3pa":   s.get("pointsThreeAttempted", 0),
                    "pf":    s.get("foulsTotal", 0),
                    "min":   parse_minutes(mins),
                })
        return players

    def get_totals(entity):
        return {
            "pts": entity.get("points", 0),
            "fgm": entity.get("fieldGoalsMade", 0),
            "fga": entity.get("fieldGoalsAttempted", 0),
            "ftm": entity.get("freeThrowsMade", 0),
            "fta": entity.get("freeThrowsAttempted", 0),
            "3pm": entity.get("pointsThreeMade", 0),
            "3pa": entity.get("pointsThreeAttempted", 0),
            "reb": entity.get("rebounds", 0),
            "orb": entity.get("reboundsOffensive", 0),
            "drb": entity.get("reboundsDefensive", 0),
            "ast": entity.get("assists", 0),
            "stl": entity.get("steals", 0),
            "blk": entity.get("blocks", 0),
            "tov": entity.get("turnovers", 0),
        }

    home_data = stats_base.get("home", {})
    away_data = stats_base.get("away", {})
    home_players = get_players(home_data)
    away_players = get_players(away_data)

    if not home_players or not away_players:
        return None

    return {
        "date":       game_date,
        "home_team":  home_team,
        "away_team":  away_team,
        "home_score": home_score,
        "away_score": away_score,
        "competition": comp_name,
        "league_id":  COMPETITION_MAP[comp_name],
        "fixture_id": fixture_top.get("fixtureId", ""),
        "stats": {
            "home": {**get_totals(home_data.get("entity", {})), "players": home_players},
            "away": {**get_totals(away_data.get("entity", {})), "players": away_players},
        }
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape NBL1 box scores.")
    parser.add_argument("--cutoff_date", type=str, default=None, help="Skip games older than YYYY-MM-DD")
    args = parser.parse_args()

    run_nbl1_scraper(cutoff_date=args.cutoff_date)
