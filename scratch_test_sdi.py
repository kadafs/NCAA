import json
import os

test_ids = [207, 208, 209, 210, 211, 212, 213, 214, 215, 216]
for lid in test_ids:
    file_path = f'data/team_stats/{lid}.json'
    if os.path.exists(file_path):
        data = json.load(open(file_path, 'r', encoding='utf-8'))
        if data:
            first_team = list(data.keys())[0]
            team_data = data[first_team]
            print(f'League {lid} | {first_team}:')
            print(f'  Model: {team_data.get("model_used")}')
            print(f'  SDI Calculated: {"sdi" in team_data}')
            if 'sdi' in team_data:
                print(f'  SDI Value: {team_data["sdi"]}')
