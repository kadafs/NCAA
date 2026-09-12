import json, sys
sys.stdout.reconfigure(encoding='utf-8')

data = json.load(open('data/football/universal_predictions_2026-09-05.json', 'r', encoding='utf-8'))
for p in data['predictions']:
    if p.get('league_id') == 39:
        mc = p.get('match_center', {})
        ht = p.get('home_team')
        at = p.get('away_team')
        btts = p.get('btts_prob')
        o25 = p.get('over_2_5_prob')
        mc_o25 = mc.get('over_2_5_prob')
        sh = mc.get('statsH', {})
        sa = mc.get('statsA', {})
        print(f"{ht:18} vs {at:18}: BTTS={btts}% | O2.5={o25}% (mc={mc_o25}%) | GP={sh.get('played')} vs {sa.get('played')} | Form={sh.get('form')} vs {sa.get('form')}")
