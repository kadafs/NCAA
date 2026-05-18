import sys

with open('run_custom_audit.py', 'r', encoding='utf-8') as f:
    original = f.read()

# We want to replace `def run_audit(search_term, limit=None, league_id_filter=None):`
# with `def get_audit_data(search_term, limit=None, league_id_filter=None):`
# and at the end of the data collection (before OUTPUT), return the data object.
# Then create `print_audit_data(data)` which takes that object and prints it.
# Then `def run_audit(...)` which calls both.

new_code = original.replace(
    'def run_audit(search_term, limit=None, league_id_filter=None):',
    'def get_audit_data(search_term, limit=None, league_id_filter=None):'
)

# Replace the output section
# Search for: # --- OUTPUT ---
output_marker = "    # --- OUTPUT ---\n"
parts = new_code.split(output_marker)

part1 = parts[0]
part2 = parts[1]

# In part1, we need to gather SDI data before returning
# SDI logic is currently in part2. Let's find it.
sdi_marker = "    # --- SDI SECTION ---\n"
sdi_parts = part2.split(sdi_marker)

output_logic = sdi_parts[0]
sdi_logic = sdi_parts[1]

# We need to extract the SDI calculation logic, which is:
"""
    if sdi_index:
        sdi_matches = []
        for team_name in all_team_names:
            t_lower = team_name.lower()
            rec = sdi_index.get(t_lower)
            if not rec and t_lower.split():
                words = t_lower.split()
                if t_lower.endswith(' w') or t_lower.endswith(' (w)'):
                    rec = sdi_index.get(words[0] + ' w')
                if not rec:
                    rec = sdi_index.get(words[0])
            
            if rec and rec not in sdi_matches:
                sdi_matches.append(rec)
        
        if sdi_matches:
            sdi_matches.sort(key=lambda x: x['avg_sdi'], reverse=True)
"""
sdi_calc = """
    sdi_matches = []
    if sdi_index:
        for team_name in all_team_names:
            t_lower = team_name.lower()
            rec = sdi_index.get(t_lower)
            if not rec and t_lower.split():
                words = t_lower.split()
                if t_lower.endswith(' w') or t_lower.endswith(' (w)'):
                    rec = sdi_index.get(words[0] + ' w')
                if not rec:
                    rec = sdi_index.get(words[0])
            
            if rec and rec not in sdi_matches:
                sdi_matches.append(rec)
        
        if sdi_matches:
            sdi_matches.sort(key=lambda x: x['avg_sdi'], reverse=True)
"""

# Append sdi calculation to part1, then return a dict
part1_modified = part1 + sdi_calc + """
    return {
        'search_term': search_term,
        'limit': limit,
        'league_id_filter': league_id_filter,
        'games_found': games_found,
        'stats': stats,
        'sdi_matches': sdi_matches,
        'all_team_names': list(all_team_names)
    }

def print_audit_data(data):
    search_term = data['search_term']
    limit = data['limit']
    league_id_filter = data['league_id_filter']
    games_found = data['games_found']
    stats = data['stats']
    sdi_matches = data['sdi_matches']
    all_team_names = data['all_team_names']

    # --- OUTPUT ---
"""

# Now we need to modify the SDI print logic in sdi_logic
sdi_print = """
    if sdi_matches:
        print("\\n" + "-"*70)
        print(" STAR DEPENDENCY INDEX (SDI) — Based on Proballers box score data")
        print("-"*70)
        print(f" {'Team':<35} {'SDI':>6} {'Top1':>5} {'Risk':<16} {'Key Stars'}")
        print(" " + "-"*90)
        for rec in sdi_matches:
            stars = ", ".join(
                f"{p['name']} (top-2 in {p['times_top2']} games)"
                for p in rec.get('top_players', [])[:2]
            )
            risk_col = rec['risk_label']
            print(f" {rec['team']:<35} {rec['avg_sdi']:>5}% {rec['avg_top1_pct']:>4}% {risk_col:<16} {stars}")
        print()
    else:
        if search_term.lower() not in [''] and len(all_team_names) > 0:
            print("\\n  [SDI] No player box-score data for this league in Proballers.")
            print("  SDI requires per-game player scoring — either this league has")
            print("  never been scraped, or was scraped before player data was captured.")
            print("  Fix: python scrape_proballers_batch.py  (then re-run calculate_sdi.py)\\n")

    print("\\n")

def run_audit(search_term, limit=None, league_id_filter=None):
    data = get_audit_data(search_term, limit, league_id_filter)
    print_audit_data(data)
"""

# Assemble final
final_code = part1_modified + output_logic + "    # --- SDI SECTION ---\n" + sdi_print

# The end of original file has def main(). We need to make sure we didn't lose it.
# Wait, def main() was after sdi_logic. Let's find it.
main_marker = "def main():\n"
if main_marker in sdi_parts[1]:
    sdi_actual_logic, main_logic = sdi_parts[1].split(main_marker)
    final_code += "\n" + main_marker + main_logic

with open('run_custom_audit.py', 'w', encoding='utf-8') as f:
    f.write(final_code)

print("Refactored run_custom_audit.py successfully.")
