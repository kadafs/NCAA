import glob, re, subprocess

reports = glob.glob('mlb/consensus_f5_v3_report_MLB_*.md')
date_files = {}
for r in reports:
    m = re.search(r'(\d{4}-\d{2}-\d{2})', r)
    if not m: continue
    d = m.group(1)
    if d in ['2026-06-18', '2026-06-19', '2026-06-20', '2026-06-21']:
        date_files.setdefault(d, []).append(r)

results = []
for d in sorted(date_files.keys()):
    files = date_files[d]
    chosen = files[0]
    for f in files:
        if 'generic' not in f.lower(): chosen = f; break
    try:
        out = subprocess.check_output(['python', 'mlb/grade_td_reports.py', '--file', chosen, '--date', d], encoding='utf-8')
        lines = out.split('\n')
        for i, line in enumerate(lines):
            if '[WIN]' in line or '[LOSS]' in line:
                game_line_str = lines[i-2].strip()
                act = lines[i-1].strip()
                res = line.strip()
                
                m_gline = re.search(r'\(Line:\s*([\d.]+)\)', game_line_str)
                gline = float(m_gline.group(1)) if m_gline else 4.5
                
                bdir = 'OVER' if 'Bet **OVER**' in act else ('UNDER' if 'Bet **UNDER**' in act else None)
                if not bdir: continue
                
                m = re.search(r'Result\s*:\s*([\d.]+)\s*runs', res)
                if not m: continue
                runs = float(m.group(1))
                
                outc = 'WIN' if '[WIN]' in res else 'LOSS'
                margin = (runs - gline) if bdir == 'OVER' else (gline - runs)
                results.append({'d': d, 'bdir': bdir, 'runs': runs, 'mrg': margin, 'outc': outc})
    except Exception as e:
        pass

def stats(group, lbl):
    tot = len(group)
    if tot == 0: 
        print(f"\n{lbl} BETS: 0 games")
        return
    w = sum(1 for r in group if r['outc']=='WIN')
    l = tot - w
    print(f'\n{lbl} BETS (June 18-21)')
    print(f'Total: {tot} | Record: {w}-{l} ({w/tot*100:.1f}%)')
    if w:
        avg_w = sum(r['runs'] for r in group if r['outc']=='WIN')/w
        print(f'  Wins Avg Runs: {avg_w:.2f}')
    if l:
        avg_l = sum(r['runs'] for r in group if r['outc']=='LOSS')/l
        print(f'  Loss Avg Runs: {avg_l:.2f}')

overs = [r for r in results if r['bdir']=='OVER']
unders = [r for r in results if r['bdir']=='UNDER']
stats(overs, 'OVER')
stats(unders, 'UNDER')
w_tot = sum(1 for r in results if r['outc']=='WIN')
print(f'\nOVERALL (June 18-21): {len(results)} bets | {w_tot}-{len(results)-w_tot} ({w_tot/len(results)*100:.1f}%)')
