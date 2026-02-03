import time
import subprocess
import os

def run_step(cmd, desc):
    print(f"\n>>> Running: {desc}")
    start = time.time()
    try:
        subprocess.run(cmd, check=True)
        duration = time.time() - start
        print(f"<<< Finished in {duration:.2f} seconds.")
        return duration
    except Exception as e:
        print(f"!!! Failed: {e}")
        return -1

steps = [
    (["python", "-m", "ncaa.fetch_barttorvik"], "NCAA Barttorvik Fetch"),
    (["python", "-m", "ncaa.v1_2.run", "--mode", "safe", "--refresh"], "NCAA Full Refresh + Run"),
    (["python", "-m", "nba.fetch_nba_schedule"], "NBA Schedule"),
    (["python", "-m", "nba.fetch_nba_stats"], "NBA Stats"),
    (["python", "-m", "nba.fetch_nba_player_stats"], "NBA Player Stats"),
    (["python", "core/supabase_pusher.py"], "Supabase Pulsher"),
    (["python", "core/audit_engine.py", "--days", "1"], "Audit Engine")
]

durations = {}
for cmd, desc in steps:
    durations[desc] = run_step(cmd, desc)

print("\n" + "="*40)
print("PIPELINE PERFORMANCE SUMMARY")
print("="*40)
total = 0
for desc, d in durations.items():
    if d >= 0:
        print(f"{desc:25}: {d:6.2f}s")
        total += d
    else:
        print(f"{desc:25}: FAILED")

print("-" * 40)
print(f"{'Total Time':25}: {total:6.2f}s ({(total/60):.2f}m)")
print("="*40)
