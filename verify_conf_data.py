import json
import sys

# Load both files
fs = json.load(open('data/barttorvik_stats.json'))
conf = json.load(open('data/barttorvik_stats_conf.json'))

# Check a sample team
team = 'Duke'
print(f"Team: {team}")
print(f"Full-Season AdjOE: {fs[team]['adj_off']:.2f}")
print(f"Conference AdjOE: {conf[team]['adj_off']:.2f}")
print(f"Difference: {abs(fs[team]['adj_off'] - conf[team]['adj_off']):.2f}")

# Check if files are identical
identical = (fs == conf)
print(f"\nFiles are identical: {identical}")

if not identical:
    print("\n SUCCESS - Conference-only data is DIFFERENT from full-season!")
    print("The D1 conference model will now use TRUE conference-only stats.")
else:
    print("\n WARNING - Files are still identical. Conference data may not have loaded correctly.")

sys.exit(0 if not identical else 1)
