import csv
with open('data/confidence_reports/confidence_2026-05-16.csv', 'r') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    rows = [r for r in rows if r.get('Score')]
    rows.sort(key=lambda x: float(x['Score']), reverse=True)
    print('Top 5 games in confidence report:')
    for r in rows[:5]:
        print(f"{r['Score']:<6} | {r['Matchup']:<40} | Vol: {r['Avg Vol']} | MAE: {r['Avg MAE']} | Bias: {r['Avg Bias']}")
