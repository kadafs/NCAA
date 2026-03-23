import json, glob
import os

leagues_adv = set()
leagues_all = set()

# Read all predictions to find all leagues and which ones ever had an ADV prediction
for f in glob.glob('data/basketball/universal_predictions_*.json'):
    try:
        with open(f, encoding='utf-8') as file:
            data = json.load(file)
            for p in data.get('predictions', []):
                league_str = f"{p.get('country')} — {p.get('league')}"
                leagues_all.add(league_str)
                if 'ADVANCED' in str(p.get('model_architecture', '')):
                    leagues_adv.add(league_str)
    except Exception as e:
        pass

srs_only = sorted(list(leagues_all - leagues_adv))
adv_leagues = sorted(list(leagues_adv))

print(f'\nTotal unique leagues tracked: {len(leagues_all)}')
print(f'Leagues WITH Proballers (Advanced): {len(adv_leagues)}')
print(f'Leagues WITHOUT Proballers (SRS only): {len(srs_only)}\n')

print('--- LEAGUES USING ONLY SRS ---')
for l in srs_only:
    print(f'- {l}')
