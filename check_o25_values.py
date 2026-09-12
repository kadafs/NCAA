import os
import glob
import json

football_files = glob.glob(r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football\*.json')
print("Sample files in Sports Analytics football:", [os.path.basename(f) for f in football_files[:20]])

# Check dates_index or predictions_latest.json
latest_file = r'c:\Users\markk\OneDrive\Desktop\CODE\Sports Analytics\public\data\football\predictions_latest.json'
if os.path.exists(latest_file):
    print("Found predictions_latest.json")
else:
    # Look for files with 'pred'
    pred_files = [f for f in football_files if 'pred' in os.path.basename(f)]
    print(f"Pred files: {[os.path.basename(f) for f in pred_files[:10]]}")

# Also check ncaa-api
ncaa_files = glob.glob(r'c:\Users\markk\OneDrive\Desktop\CODE\ncaa-api\data\football\*.json')
print("ncaa-api football files:", [os.path.basename(f) for f in ncaa_files[:20]])
