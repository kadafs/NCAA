import glob, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for root in [r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football', r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\football']:
    files = glob.glob(os.path.join(root, 'universal_predictions_*.json'))
    print(f"Found in {root}:", len(files))
    if files:
        for f in sorted(files)[-5:]:
            print("  ", os.path.basename(f), f"{os.path.getsize(f)} bytes")
