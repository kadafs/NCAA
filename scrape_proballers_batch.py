"""
scrape_proballers_batch.py
--------------------------
Off-peak batch scraper for all Proballers-registered leagues.
Run this overnight or on weekends — it will scrape box-score data
from each league's Proballers schedule page and save it to the
data/historical/ folder, enabling the ADV model for each league.

Usage:
    python scrape_proballers_batch.py
    python scrape_proballers_batch.py --cutoff_date 2025-10-01
    python scrape_proballers_batch.py --max 150
"""
import argparse
import subprocess
import sys
import time

# ---------------------------------------------------------------
# Leagues registered for Proballers ADV upgrades.
# Focused on mid-season leagues that still need player box-score
# data for SDI calculations. European leagues are excluded here
# as their season is ending — they'll be added next October.
#
# Format: (display_label, proballers_schedule_url)
# Note: UK SLB has no api-basketball ID but is still scraped for ADV data.
# ---------------------------------------------------------------
PROBALLERS_LEAGUES = [
    # --- North America ---
    ("NBA",                  "https://www.proballers.com/basketball/league/3/nba/schedule"),
    ("WNBA",                 "https://www.proballers.com/basketball/league/397/wnba/schedule"),
    ("Puerto Rico BSN",      "https://www.proballers.com/basketball/league/270/puerto-rico-bsn/schedule"),
    ("UK SLB",               "https://www.proballers.com/basketball/league/120/british-sbl/schedule"),
    ("Venezuela Superliga",  "https://www.proballers.com/basketball/league/100107/venezuela-spb/schedule"),
    ("Uruguay Liga Uruguaya","https://www.proballers.com/basketball/league/356/uruguay-liga/schedule"),
    # --- Asia / Middle East ---
    ("Turkey TBL",           "https://www.proballers.com/basketball/league/348/turkey-tbl/schedule"),
    ("Russia VTB",           "https://www.proballers.com/basketball/league/272/vtb-united-league/schedule"),
]

def main():
    parser = argparse.ArgumentParser(description="Off-peak batch Proballers scraper")
    parser.add_argument("--cutoff_date", default="2025-10-01",
                        help="Do not scrape games older than this date (default: 2025-10-01)")
    parser.add_argument("--max", type=int, default=200,
                        help="Max games per league (default: 200)")
    parser.add_argument("--delay", type=int, default=10,
                        help="Seconds to pause between leagues (default: 10)")
    args = parser.parse_args()

    total = len(PROBALLERS_LEAGUES)
    print(f"\n{'='*60}")
    print(f"  PROBALLERS BATCH SCRAPER — {total} leagues")
    print(f"  Cutoff: {args.cutoff_date}  |  Max games/league: {args.max}")
    print(f"{'='*60}\n")

    for i, (label, url) in enumerate(PROBALLERS_LEAGUES, 1):
        print(f"[{i}/{total}] {label}")
        print(f"  URL: {url}")
        cmd = [
            sys.executable, "scrape_proballers.py",
            "--url", url,
            "--cutoff_date", args.cutoff_date,
            "--max", str(args.max),
        ]
        result = subprocess.run(cmd, capture_output=False)
        if result.returncode != 0:
            print(f"  [!] {label} finished with errors (exit {result.returncode})")
        else:
            print(f"  [OK] {label} done.")

        if i < total:
            print(f"  Pausing {args.delay}s before next league...\n")
            time.sleep(args.delay)

    print(f"\n{'='*60}")
    print("  Batch scrape complete!")
    print("  Next steps:")
    print("    python generate_advanced_metrics.py")
    print("    python aggregate_basketball_stats.py")
    print("    python push_to_dashboard.py --sport basketball")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
