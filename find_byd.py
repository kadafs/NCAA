import csv
with open('data/confidence_reports/confidence_2026-05-16.csv', 'r') as f:
    reader = csv.DictReader(f)
    for r in reader:
        if 'Bydgoszcz' in r.get('Matchup', ''):
            print(f"{r['Score']} | {r['Matchup']} | Vol: {r['Avg Vol']} | MAE: {r['Avg MAE']} | Tiers: {r['Tiers']}")
