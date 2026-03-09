import os
import json
import subprocess
import argparse
from datetime import datetime

# All 5 English football leagues
ENGLISH_LEAGUES = [
    ("epl",              "Premier League"),
    ("eng_championship", "Championship"),
    ("eng_league_one",   "League One"),
    ("eng_league_two",   "League Two"),
    ("eng_national",     "National League"),
]

def main():
    parser = argparse.ArgumentParser(description="Batch Runner for English Football Leagues (All 5 Tiers)")
    parser.add_argument("--mode", choices=["safe", "full"], default="full", help="Prediction mode")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print("=" * 70)
    print(f" BATCH RUN: 5 ENGLISH FOOTBALL LEAGUES | MODE: {args.mode.upper()}")
    print(f" Date: {target_date}")
    print("=" * 70)

    base_cmd = ["python", "run_universal.py", "--sport", "football", "--mode", args.mode]
    if args.refresh:
        base_cmd.append("--refresh")
    if args.trace:
        base_cmd.append("--trace")
    if args.date:
        base_cmd += ["--date", args.date]

    for idx, (code, name) in enumerate(ENGLISH_LEAGUES, 1):
        print(f"\n[{idx}/5] {name} ({code.upper()})")
        print("-" * 50)

        cmd = base_cmd + ["--league", code]
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                errors='replace'
            )
            for line in process.stdout:
                print(line, end="")
            process.wait()

            if process.returncode != 0:
                print(f"  [!] {name} exited with code {process.returncode}")
        except Exception as e:
            print(f"  [!] Exception running {code}: {e}")

    # --- Merge all per-league predictions into a combined output ---
    combined = []
    for code, name in ENGLISH_LEAGUES:
        league_file = f"data/football/{code}_predictions.json"
        if os.path.exists(league_file):
            with open(league_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            combined.extend(records)
            print(f"  Collected {len(records)} records from {code}")

    if combined:
        out_path = f"data/football/english_leagues_predictions_{target_date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)
        print(f"\nCombined output saved -> {out_path}  ({len(combined)} total predictions)")

    print("\n" + "=" * 70)
    print(" BATCH RUN COMPLETE: English Leagues")
    print("=" * 70)

if __name__ == "__main__":
    main()

