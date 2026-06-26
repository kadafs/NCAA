import json
import sys, os
sys.path.append(os.path.abspath('mlb'))
from park_factors import get_park_factor_details

with open('data/baseball/universal_predictions_2026-06-26-confirmed.json') as f:
    data = json.load(f)

for g in data['predictions']:
    venue = g['environment']['venue']
    pf_details = get_park_factor_details(venue)
    static = pf_details.get('static', 1.0)
    real = pf_details.get('realized', 1.0)
    diff = real - static
    if abs(diff) > 0.15:
        print(f"[{venue}] Diff: {diff:.3f} | Static: {static} | Real: {real}")
    
    weather_lbl = g['environment']['weather']['weather_label'].lower()
    is_roof = any(p in venue.lower() for p in ['daikin', 'chase', 'globe life', 'minute maid'])
    is_closed = 'dome' in weather_lbl or 'roof closed' in weather_lbl
    if is_roof and is_closed:
        print(f"[{venue}] ROOF CLOSED PROTOCOL TRIGGERED")
