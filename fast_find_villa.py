import os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root in ['data/football', r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public']:
    for dirpath, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.next', 'dist')]
        for fn in filenames:
            if fn.endswith('.json'):
                fp = os.path.join(dirpath, fn)
                try:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        txt = f.read()
                    if 'Aston Villa' in txt and 'Nottingham Forest' in txt:
                        print(f"FOUND in {fp} ({os.path.getsize(fp)} bytes)")
                except Exception:
                    pass
