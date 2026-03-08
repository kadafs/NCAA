import os
import subprocess
import argparse

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
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("=" * 70)
    print(f" BATCH RUN: 5 ENGLISH FOOTBALL LEAGUES | MODE: {args.mode.upper()}")
    print("=" * 70)

    base_cmd = ["python", "run_universal.py", "--sport", "football", "--mode", args.mode]
    if args.refresh:
        base_cmd.append("--refresh")
    if args.trace:
        base_cmd.append("--trace")

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

    print("\n" + "=" * 70)
    print(" BATCH RUN COMPLETE: English Leagues")
    print("=" * 70)

if __name__ == "__main__":
    main()
