import os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root, dirs, files in os.walk('.'):
    if '.git' in root or 'node_modules' in root or '.venv' in root or '__pycache__' in root:
        continue
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                content = open(p, 'r', encoding='utf-8', errors='ignore').read()
                if 'match_center' in content:
                    print(f"Found 'match_center' in {p}")
            except Exception as e:
                pass
