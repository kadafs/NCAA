import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('data/football/universal_predictions_2026-09-12.json', 'r', encoding='utf-8'))
for p in data['predictions']:
    if p.get('league_id') == 39:
        mc = p.get('match_center', {})
        sh = mc.get('statsH', {})
        sa = mc.get('statsA', {})
        print(f"{p['home_team']:18} vs {p['away_team']:18}: BTTS={p['btts_prob']}% | O2.5={p['over_2_5_prob']}% (mc={mc.get('over_2_5_prob')}%) | GP={sh.get('played')} vs {sa.get('played')} | Form={sh.get('form')} vs {sa.get('form')}")
