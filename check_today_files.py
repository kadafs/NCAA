import os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root in ['data/football', '../Sports Analytics/public/data/football']:
    for d in ['2026-09-11', '2026-09-12', '2026-09-13']:
        f = os.path.join(root, f'universal_predictions_{d}.json')
        if os.path.exists(f):
            print(f"FOUND: {f} ({os.path.getsize(f)} bytes)")
        else:
            print(f"Not found: {f}")
