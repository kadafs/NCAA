import glob, os, sys, json
sys.stdout.reconfigure(encoding='utf-8')

for root in [r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public', r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data']:
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            if f.endswith('.json'):
                p = os.path.join(dirpath, f)
                try:
                    with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                        txt = fp.read()
                    if 'Aston Villa' in txt and 'Nottingham' in txt:
                        print(f"FOUND in {p} ({len(txt)} bytes)")
                except Exception as e:
                    pass
