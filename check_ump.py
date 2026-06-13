import json
db = json.load(open('data/umpires.json', 'r'))
print('Total umpires:', len(db)-1)
pks = db.get('_processed_pks', [])
print('Processed games:', len(pks))
print('Max PK:', max(pks) if pks else 0)
