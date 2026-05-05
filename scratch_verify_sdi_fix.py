import sys
sys.stdout.reconfigure(encoding='utf-8')
from run_daily_sdi_report import load_sdi_index, get_sdi_record

idx = load_sdi_index()
print(f'Index size: {len(idx)} keys')
print()

test_cases = [
    ('Maccabi Kiryat Gat',          'Should be NO MATCH (Israeli domestic, not in Proballers)'),
    ('Maccabi Maale Adumim',        'Should be NO MATCH (Israeli domestic, not in Proballers)'),
    ('Maccabi Playtika Tel Aviv',    'Should MATCH (is in Euroleague Proballers data)'),
    ('Hapoel Tel Aviv',              'May or may not match'),
    ('Real Madrid',                  'Should MATCH (in Euroleague data)'),
]

for team, note in test_cases:
    rec = get_sdi_record(team, idx)
    if rec:
        matched_name = rec['team']
        sdi_val = rec['avg_sdi']
        correct = matched_name.lower() == team.lower()
        flag = 'OK' if correct else 'WRONG MATCH'
        print(f'  [{flag}] {team}')
        print(f'         -> Resolved to: {matched_name}  (SDI={sdi_val}%)')
    else:
        print(f'  [NO MATCH] {team}')
    print(f'         Note: {note}')
    print()
