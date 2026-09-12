import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

dates_path = r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football\dates_index.json'
if os.path.exists(dates_path):
    with open(dates_path, 'r', encoding='utf-8') as f:
        print("dates_index:", json.load(f))
