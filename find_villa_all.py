import os, sys, glob
sys.stdout.reconfigure(encoding='utf-8')

# Search for any file with 'Nottingham' and 'Aston Villa'
matches = []
for root in ['data/football', '../Sports Analytics']:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith('.json') or fn.endswith('.txt'):
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if 'Aston Villa' in content and 'Nottingham Forest' in content:
                        matches.append(fp)
                except Exception:
                    pass

print(f"Total matching files: {len(matches)}")
for m in matches:
    print(" ", m, os.path.getsize(m), "bytes")
