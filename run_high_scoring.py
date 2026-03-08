import os
import sys
import subprocess
import argparse

# The 22 high-scoring leagues we added
HIGH_SCORING_LEAGUES = [
    'hk_1st', 'eng_dev_2', 'eng_pl_2', 'wales_champ', 'aus_landesliga', 
    'scot_highland', 'scot_lowland', 'ind_ileague', 'cro_1nl', 
    'swe_div1_norra', 'uefa_cl', 'nor_div1', 'den_superliga', 
    'ger_reg_west', 'eng_isthmian', 'lat_1liga', 'crc_segunda', 
    'ned_eredivisie', 'scot_prem', 'ban_pl', 'tha_pl', 'swe_damallsvenskan'
]

def main():
    parser = argparse.ArgumentParser(description="Batch Runner for High-Scoring Football Leagues")
    parser.add_argument("--mode", choices=["safe", "full"], default="full", help="Prediction mode")
    parser.add_argument("--refresh", action="store_true", help="Refresh data before running")
    parser.add_argument("--trace", action="store_true", help="Show logic trace")
    parser.add_argument("--date", help="Target date in YYYY-MM-DD format (default: today)")
    args = parser.parse_args()

    # Move to project root to run the universal script
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    print("================================================================")
    print(f" BATCH RUN: 22 HIGH-SCORING LEAGUES | MODE: {args.mode.upper()}")
    print("================================================================\n")

    base_cmd = ["python", "run_universal.py", "--sport", "football", "--mode", args.mode]
    if args.refresh:
        base_cmd.append("--refresh")
    if args.trace:
        base_cmd.append("--trace")
    if args.date:
        base_cmd += ["--date", args.date]

    for idx, league in enumerate(HIGH_SCORING_LEAGUES, 1):
        print(f"\n[{idx}/22] Running {league.upper()}...")
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

    print("\n================================================================")
    print(" BATCH RUN COMPLETE: High-Scoring Leagues")
    print("================================================================\n")

if __name__ == "__main__":
    main()
