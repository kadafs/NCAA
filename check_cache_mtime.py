import os, time, sys
sys.stdout.reconfigure(encoding='utf-8')

p = 'data/football/universal_39_stats.json'
if os.path.exists(p):
    print(f"File: {p}")
    print(f"Modified: {time.ctime(os.path.getmtime(p))}")
    print(f"Age in days: {(time.time() - os.path.getmtime(p)) / 86400:.2f}")

# Also check other universal_*_stats.json files
for f in os.listdir('data/football'):
    if f.startswith('universal_') and f.endswith('_stats.json'):
        fp = os.path.join('data/football', f)
        print(f"  {f}: {time.ctime(os.path.getmtime(fp))}")
