"""
calibrate_milb_pf.py
====================
Pulls real AAA/AA game results from the 2026 season via statsapi (using
schedule hydration to get linescores in bulk — one API call per day instead
of one per game), computes actual average F5 runs per venue, and derives
empirical park factors to compare against hand-crafted static estimates.

Usage:
    python mlb/calibrate_milb_pf.py              # full 2026 AAA season
    python mlb/calibrate_milb_pf.py --days 30    # last 30 days
    python mlb/calibrate_milb_pf.py --sport 12   # AA instead
"""

import statsapi
import json
import os
import argparse
from datetime import datetime, timedelta
from collections import defaultdict

SPORT_ID     = 11
SEASON_START = "2026-04-01"
MIN_GAMES    = 5

CURRENT_PF = {
    # AAA PCL
    "Las Vegas Ballpark":           1.250,
    "Constellation Field":          1.185,
    "Greater Nevada Field":         1.180,
    "Chickasaw Bricktown Ballpark": 1.160,
    "Isotopes Park":                1.150,
    "Hodgetown":                    1.140,
    "Principal Park":               1.110,
    "Momentum Bank Ballpark":       1.100,
    "Round Rock":                   1.095,
    "Toyota Field":                 1.070,
    # AAA IL
    "Truist Field":                 1.050,
    "Louisville Slugger Field":     1.040,
    "Victory Field":                1.030,
    "Harbor Park":                  1.025,
    "Polar Park":                   1.020,
    "AutoZone Park":                1.015,
    "Gwinnett Field":               1.010,
    "Sahlen Field":                 0.995,
    "Coca-Cola Park":               0.990,
    "VyStar Ballpark":              0.988,
    "Vystar Ballpark":              0.988,
    "Durham Bulls Athletic Park":   0.985,
    "Dunkin Park":                  0.982,
    # AA EL
    "Delta Dental Stadium":         1.005,
    "TD Bank Ballpark":             1.000,
    "UPMC Park":                    0.985,
    "7 17 Credit Union Park":       0.980,
    "Peoples Natural Gas Field":    0.978,
    # AA SL
    "Covenant Health Park":         1.005,
    "Synovus Park":                 1.015,
    "Blue Wahoos Stadium":          0.988,
    "Riverwalk Stadium":            1.020,
    # AA TL
    "Whataburger Field":            1.080,
    "ONEOK Field":                  1.070,
    "Equity Bank Park":             1.065,
    "Arvest Ballpark":              1.055,
    "Dickey-Stephens Park":         1.045,
    "Nelson Wolff Stadium":         1.090,
    "Dr Pepper Ballpark":           1.075,
    "Hammons Field":                1.035,
}


def get_static_pf(venue):
    for name, pf in CURRENT_PF.items():
        if name.lower() in venue.lower() or venue.lower() in name.lower():
            return pf
    return 1.00


def main():
    parser = argparse.ArgumentParser(description="Calibrate MiLB Park Factors from real game data")
    parser.add_argument("--days",  type=int, default=None, help="Only last N days (default: full season)")
    parser.add_argument("--sport", type=int, default=SPORT_ID, help="11=AAA, 12=AA")
    args = parser.parse_args()

    today = datetime.today()
    start = (today - timedelta(days=args.days)).strftime("%Y-%m-%d") if args.days else SEASON_START
    end   = today.strftime("%Y-%m-%d")
    label = {11: "AAA", 12: "AA"}.get(args.sport, f"sport{args.sport}")

    print(f"\n=== MiLB Park Factor Calibration ({label}) ===")
    print(f"Date range: {start} to {end}")
    print("Strategy: bulk schedule+linescore hydration (one API call per day)\n")

    venue_f5   = defaultdict(list)
    venue_full = defaultdict(list)

    current    = datetime.strptime(start, "%Y-%m-%d")
    end_dt     = datetime.strptime(end,   "%Y-%m-%d")
    total_days = (end_dt - current).days + 1
    day_n      = 0
    games_seen = 0

    while current <= end_dt:
        ds = current.strftime("%m/%d/%Y")
        try:
            data = statsapi.get("schedule", {
                "sportId": args.sport,
                "date":    ds,
                "hydrate": "linescore",
            })
            for date_obj in data.get("dates", []):
                for game in date_obj.get("games", []):
                    # Only final games
                    if game.get("status", {}).get("abstractGameState") != "Final":
                        continue
                    venue = game.get("venue", {}).get("name", "")
                    if not venue:
                        continue
                    innings = game.get("linescore", {}).get("innings", [])
                    if not innings:
                        continue

                    # F5 total
                    f5 = 0
                    for inn in innings[:5]:
                        f5 += int(inn.get("away", {}).get("runs", 0) or 0)
                        f5 += int(inn.get("home", {}).get("runs", 0) or 0)

                    # Full game total
                    teams  = game.get("teams", {})
                    away_s = teams.get("away", {}).get("score", 0) or 0
                    home_s = teams.get("home", {}).get("score", 0) or 0

                    venue_f5[venue].append(f5)
                    venue_full[venue].append(away_s + home_s)
                    games_seen += 1

        except Exception as exc:
            print(f"  Warning: {ds} error — {exc}")

        current += timedelta(days=1)
        day_n   += 1
        if day_n % 10 == 0:
            print(f"  Day {day_n}/{total_days} processed ({games_seen} games so far)...", flush=True)

    # League averages
    all_f5   = [x for vals in venue_f5.values() for x in vals]
    all_full = [x for vals in venue_full.values() for x in vals]

    if not all_f5:
        print("ERROR: No F5 data retrieved — check internet / statsapi.")
        return

    league_avg_f5   = sum(all_f5) / len(all_f5)
    league_avg_full = sum(all_full) / len(all_full) if all_full else 0

    print(f"\nLeague averages ({label}):")
    print(f"  F5   avg : {league_avg_f5:.3f} runs/game  ({len(all_f5)} games)")
    print(f"  Full avg : {league_avg_full:.3f} runs/game")

    # Build per-venue rows
    rows = []
    for venue in sorted(venue_f5.keys()):
        lst = venue_f5[venue]
        n   = len(lst)
        if n < MIN_GAMES:
            continue
        avg_f5     = sum(lst) / n
        emp_pf     = round(avg_f5 / league_avg_f5, 4)
        current_pf = get_static_pf(venue)
        delta      = round(emp_pf - current_pf, 4)
        rows.append(dict(
            venue=venue, n=n,
            avg_f5=round(avg_f5, 3),
            emp_pf=emp_pf,
            current_pf=current_pf,
            delta=delta,
        ))

    rows.sort(key=lambda r: r["emp_pf"], reverse=True)

    # Print table
    print(f"\n{'Venue':<36} {'N':>4}  {'AvgF5':>6}  {'EmpPF':>7}  {'CurPF':>7}  {'Delta':>7}")
    print("-" * 75)
    for r in rows:
        flag = "  << OVER-EST" if r["delta"] < -0.05 else ("  << UNDER-EST" if r["delta"] > 0.05 else "")
        print(f"{r['venue']:<36} {r['n']:>4}  {r['avg_f5']:>6.3f}  "
              f"{r['emp_pf']:>7.4f}  {r['current_pf']:>7.4f}  {r['delta']:>+7.4f}{flag}")

    print("\n" + "=" * 75)
    print("CORRECTIONS NEEDED (|delta| > 0.03):")
    corrections = [r for r in rows if abs(r["delta"]) > 0.03]
    if corrections:
        for r in corrections:
            direction = "LOWER" if r["delta"] < 0 else "RAISE"
            print(f"  {direction:<6} {r['venue']:<34}  {r['current_pf']:.4f} -> {r['emp_pf']:.4f}  ({r['delta']:>+.4f})")
    else:
        print("  All static PFs within 3% of empirical values — no corrections needed.")

    # Save corrected JSON
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"calibrated_pf_{label}_{today.strftime('%Y-%m-%d')}.json",
    )
    with open(out_path, "w") as f:
        json.dump({r["venue"]: r["emp_pf"] for r in rows}, f, indent=2)
    print(f"\nCalibrated PF table saved -> {out_path}")


if __name__ == "__main__":
    main()
