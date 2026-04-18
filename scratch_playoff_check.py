import json
import glob

print("Checking recent predictions for playoff indicators...")
for f in sorted(glob.glob('data/basketball/universal_predictions_*.json'))[-3:]:
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
            for p in data.get('predictions', []):
                # Print some keys to see what's available
                print(f"Keys for a prediction: {list(p.keys())}")
                break
    except Exception as e:
        print(e)
    break
