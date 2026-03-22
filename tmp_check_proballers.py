import glob, json, os
from collections import defaultdict

p_files = glob.glob('C:/Users/markk/OneDrive/Desktop/CODE/ncaa-api/data/historical/proballers_*.json')
low_match_teams = {}

for f in p_files:
    try:
        data = json.load(open(f, encoding='utf-8'))
        if not isinstance(data, list): continue
        
        team_counts = defaultdict(int)
        for m in data:
            home = m.get('home_team')
            away = m.get('away_team')
            if home: team_counts[home] += 1
            if away: team_counts[away] += 1
            
        under_10 = {k: v for k, v in team_counts.items() if v < 10}
        
        if under_10:
            league_slug = os.path.basename(f).replace('proballers_', '').replace('.json', '')
            low_match_teams[league_slug] = under_10
            
    except Exception as e:
        print(f"Error reading {f}: {e}")

total_teams = sum(len(v) for v in low_match_teams.values())

out_file = 'C:/Users/markk/.gemini/antigravity/brain/0a479f50-45bd-412d-993d-60f275dc267e/low_match_teams_report.md'
with open(out_file, 'w', encoding='utf-8') as out:
    out.write('# Proballers Data Audit: Teams with < 10 Matches\\n\\n')
    out.write(f'Scanned **{len(p_files)}** Proballers league files.\\n')
    out.write(f'Found **{total_teams}** teams with fewer than 10 historical matches scraped.\\n\\n')
    
    if total_teams == 0:
        out.write('✅ All teams currently recorded have at least 10 matches of history.')
    else:
        for league, teams in sorted(low_match_teams.items()):
            out.write(f'### {league.upper().replace("-", " ")}\\n')
            out.write('| Team Name | Matches Scraped |\\n')
            out.write('|-----------|-----------------|\\n')
            for t_name, count in sorted(teams.items(), key=lambda x: x[1]):
                out.write(f'| {t_name} | {count} |\\n')
            out.write('\\n')

print(f"Report generated successfully. Found {total_teams} teams.")
