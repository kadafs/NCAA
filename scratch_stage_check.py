import json
import glob

stages = set()
for f in glob.glob('data/basketball/universal_predictions_*.json'):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
            for p in data.get('predictions', []):
                stage = p.get('stage')
                if stage:
                    stages.add(stage)
    except Exception as e:
        pass

for s in sorted(stages):
    print(s)
