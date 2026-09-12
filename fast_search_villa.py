import glob, sys, re
sys.stdout.reconfigure(encoding='utf-8')

for f in glob.glob('data/football/universal_predictions_*.json'):
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
        if '"Aston Villa"' in content and '"Nottingham Forest"' in content:
            print(f"FOUND MATCH in {f}")
