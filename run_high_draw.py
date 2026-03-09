import os
import json
import subprocess
import argparse
from datetime import datetime

# The 15 high-draw leagues we added
HIGH_DRAW_LEAGUES = [
    'par_primera_ap', 'usa_mls', 'ven_primera', 'spa_tercera_6', 
    'hon_liga_nac', 'spa_tercera_18', 'ecu_primera_b', 'arg_nacional_b', 
    'arg_primera', 'ita_serie_b', 'col_primera_a', 'arg_primera_b', 
    'fra_national', 'egy_prem', 'uru_apertura'
]

def main():
    parser = argparse.ArgumentParser(description="Batch Runner for High-Draw Football Leagues")
    parser.add_argument("--mode", choices=["safe", "full"], default="full", help="Prediction mode")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    # Move to project root to run the universal script
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    target_date = args.date or datetime.now().strftime("%Y-%m-%d")

    print("================================================================")
    print(f" BATCH RUN: 15 HIGH-DRAW LEAGUES | MODE: {args.mode.upper()}")
    print(f" Date: {target_date}")
    print("================================================================\n")

    base_cmd = ["python", "run_universal.py", "--sport", "football", "--mode", args.mode]
    if args.refresh:
        base_cmd.append("--refresh")
    if args.trace:
        base_cmd.append("--trace")
    if args.date:
        base_cmd += ["--date", args.date]

    for idx, league in enumerate(HIGH_DRAW_LEAGUES, 1):
        print(f"\n[{idx}/15] Running {league.upper()}...")
        print("-" * 50)
        
        cmd = base_cmd + ["--league", league]
        try:
            # Capture output and print it as it comes
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
    for league in HIGH_DRAW_LEAGUES:
        league_file = f"data/football/{league}_predictions.json"
        if os.path.exists(league_file):
            with open(league_file, "r", encoding="utf-8") as f:
                records = json.load(f)
            if records:
                combined.extend(records)
                print(f"  Collected {len(records)} records from {league}")

    if combined:
        out_path = f"data/football/high_draw_predictions_{target_date}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)
        print(f"\nCombined output saved -> {out_path}  ({len(combined)} total predictions)")

    print("\n================================================================")
    print(" BATCH RUN COMPLETE: High-Draw Leagues")
    print("================================================================\n")

if __name__ == "__main__":
    main()
