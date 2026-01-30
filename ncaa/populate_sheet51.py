import csv
import json
import os
import sys

# Add project root to path to allow imports from utils
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES

def populate_csv():
    # File paths
    input_csv_path = os.path.join('data', 'NCAA JAN 29 - Sheet51.csv')
    stats_json_path = os.path.join('data', 'barttorvik_stats.json')
    
    # Check if files exist
    if not os.path.exists(input_csv_path):
        print(f"Error: Input CSV not found at {input_csv_path}")
        return
    if not os.path.exists(stats_json_path):
        print(f"Error: Stats JSON not found at {stats_json_path}")
        return

    # Load stats
    with open(stats_json_path, 'r') as f:
        stats_data = json.load(f)
    
    # Get list of teams keys for matching
    # Sort by length descending to match longest names first (e.g. "North Florida" before "Florida")
    team_keys = sorted(list(stats_data.keys()), key=len, reverse=True)

    # Read CSV
    with open(input_csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # New columns to add
    new_columns = [
        'AdjT_A', 'AdjT_H', 
        'AdjOE_A', 'AdjOE_H', 
        'AdjDE_A', 'AdjDE_H', 
        'eFG_A', 'eFG_H', 
        'TO_A', 'TO_H', 
        'OR_A', 'OR_H', 
        'FTR_A', 'FTR_H'
    ]
    
    # Update fieldnames if they don't exist
    for col in new_columns:
        if col not in fieldnames:
            fieldnames.append(col)

    # Process rows
    for row in rows:
        matchup = row.get('Matchup', '')
        if not matchup or ' vs ' not in matchup:
            continue
            
        parts = matchup.split(' vs ')
        if len(parts) != 2:
            continue
            
        away_raw = parts[0].strip()
        home_raw = parts[1].strip()
        
        # Find matches
        # Note: Passing dictionary keys as list for the target_list
        away_team = find_team_in_dict(away_raw, team_keys, BASKETBALL_ALIASES)
        home_team = find_team_in_dict(home_raw, team_keys, BASKETBALL_ALIASES)
        
        if not away_team:
            print(f"Warning: Could not find stats for Away team: {away_raw}")
        if not home_team:
            print(f"Warning: Could not find stats for Home team: {home_raw}")
            
        # Extract stats
        # Away Stats
        if away_team and away_team in stats_data:
            s = stats_data[away_team]
            row['AdjT_A'] = s.get('adj_t', '')
            row['AdjOE_A'] = s.get('adj_off', '')
            row['AdjDE_A'] = s.get('adj_def', '')
            row['eFG_A'] = s.get('efg', '')
            row['TO_A'] = s.get('to', '')
            row['OR_A'] = s.get('or', '')
            row['FTR_A'] = s.get('ftr', '')
            
        # Home Stats
        if home_team and home_team in stats_data:
            s = stats_data[home_team]
            row['AdjT_H'] = s.get('adj_t', '')
            row['AdjOE_H'] = s.get('adj_off', '')
            row['AdjDE_H'] = s.get('adj_def', '')
            row['eFG_H'] = s.get('efg', '')
            row['TO_H'] = s.get('to', '')
            row['OR_H'] = s.get('or', '')
            row['FTR_H'] = s.get('ftr', '')

    # Write back to CSV
    # Using same path to overwrite as requested (implied by "populate the csv file")
    with open(input_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print(f"Successfully updated {input_csv_path}")

if __name__ == "__main__":
    populate_csv()
