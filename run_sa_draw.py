import os
import json
import subprocess
import argparse
from datetime import datetime

# Secondary South American draw groups (those not already in the main run_high_draw list)
SA_DRAW_LEAGUES = [
    'bra_serie_a',
    'bra_serie_b', 
    'chi_primera',
    'bol_primera',
    'per_primera',
    'ecu_primera_a',
    'uru_clausura',
    'par_primera_cl',
    'col_primera_b'
]

def main():
    parser = argparse.ArgumentParser(description="Batch Runner for Secondary SA Draw Leagues")
    parser.add_argument("--mode", choices=["safe", "full"], default="full", help="Prediction mode")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print("================================================================")
    print(f" BATCH RUN: {len(SA_DRAW_LEAGUES)} SA DRAW LEAGUES | MODE: {args.mode.upper()}")
    print(f" Date: {target_date}")
    print("================================================================\n")

    base_cmd = ["python", "run_universal.py", "--sport", "football", "--mode", args.mode]
    if args.refresh:
        base_cmd.append("--refresh")
    if args.trace:
        base_cmd.append("--trace")
    if args.date:
        base_cmd += ["--date", args.date]

    for idx, league in enumerate(SA_DRAW_LEAGUES, 1):
        print(f"\n[{idx}/{len(SA_DRAW_LEAGUES)}] Running {league.upper()}...")
        print("-" * 50)
        
        cmd = base_cmd + ["--league", league]
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
                print(f"  [!] Failed to execute {league} (Exit code: {process.returncode})")
        except Exception as e:
            print(f"  [!] Exception running {league}: {e}")

    # --- Merge all per-league predictions into a combined output ---
    combined = []
    for league in SA_DRAW_LEAGUES:
        league_file = f"data/football/{league}_predictions.json"
        if os.path.exists(league_file):
            with open(league_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            if records:
                combined.extend(records)
                print(f"  Collected {len(records)} records from {league}")

    if combined:
        out_path = f"data/football/sa_draw_predictions_{target_date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)
        print(f"\nCombined output saved -> {out_path}  ({len(combined)} total predictions)")

    print("\n================================================================")
    print(" BATCH RUN COMPLETE: SA Draw Leagues")
    print("================================================================\n")

if __name__ == "__main__":
    main()
