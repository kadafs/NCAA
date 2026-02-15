import json
import os

filepath = os.path.abspath('data/barttorvik_raw_conf.json')
if not os.path.exists(filepath):
    print(f"File not found: {filepath}")
    exit(1)

with open(filepath, 'r') as f:
    data = json.load(f)

print(f"Loaded {len(data)} teams from raw file")

games_count = []
valid_entries = 0
for team_row in data:
    # Need at least enough columns.
    # We saw Indiana row in Step 331 has "17", "25" in index 5 and 6
    if len(team_row) > 6:
        try:
            # Index 6 is "Games" played
            g = int(team_row[6])
            games_count.append(g)
            valid_entries += 1
        except (ValueError, IndexError):
            pass

if not games_count:
    print("Could not parse 'Games' column (index 6).")
    exit(1)

avg_games = sum(games_count) / len(games_count)
print(f"Average games played per team: {avg_games:.1f}")

if avg_games > 20:
    print("\nCONCLUSION: This is FULL SEASON data (avg > 20 games)")
    print("Conference-only data should have ~10-15 games per team.")
else:
    print("\nCONCLUSION: This looks like CONFERENCE data (avg < 20 games)")
