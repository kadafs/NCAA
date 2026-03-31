import json
import os

dates = ['2026-03-26', '2026-03-27', '2026-03-28', '2026-03-29', '2026-03-30']
for d in dates:
    path = f"data/basketball/universal_predictions_{d}.json"
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            predictions = data.get('predictions', [])
            total = len(predictions)
            graded = len([p for p in predictions if p.get('actual_result') is not None])
            print(f"{d}: {graded} / {total} graded")
    else:
        print(f"{d}: File not found")
