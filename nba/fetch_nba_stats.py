import json
import os
import time
from nba_api.stats.endpoints import leaguedashteamstats

# Output path
OUTPUT_FILE = "data/nba_stats.json"

def fetch_nba_advanced_stats():
    print("Fetching NBA Advanced Stats from official API...")
    
    try:
        # Fetch Advanced Stats (Efficiency, Pace, etc.)
        advanced_stats = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Advanced',
            season='2025-26', # Update for current season
            season_type_all_star='Regular Season'
        ).get_dict()

        # Fetch Four Factors
        four_factors = leaguedashteamstats.LeagueDashTeamStats(
            measure_type_detailed_defense='Four Factors',
            season='2025-26',
            season_type_all_star='Regular Season'
        ).get_dict()

        headers_adv = advanced_stats['resultSets'][0]['headers']
        rows_adv = advanced_stats['resultSets'][0]['rowSet']
        
        headers_ff = four_factors['resultSets'][0]['headers']
        rows_ff = four_factors['resultSets'][0]['rowSet']

        processed_data = {}

        # Merge everything into a clean JSON structure
        for i, row in enumerate(rows_adv):
            row_dict_adv = dict(zip(headers_adv, row))
            team_name = row_dict_adv['TEAM_NAME']
            
            # Find corresponding four factors row
            row_dict_ff = {}
            for row_f in rows_ff:
                if row_f[headers_ff.index('TEAM_NAME')] == team_name:
                    row_dict_ff = dict(zip(headers_ff, row_f))
                    break

            processed_data[team_name] = {
                "adj_off": row_dict_adv['OFF_RATING'],
                "adj_def": row_dict_adv['DEF_RATING'],
                "adj_t": row_dict_adv['PACE'],
                "efg": row_dict_ff['EFG_PCT'] * 100,
                "efg_d": row_dict_ff['OPP_EFG_PCT'] * 100,
                "ftr": row_dict_ff['FTA_RATE'] * 100,
                "ftr_d": row_dict_ff['OPP_FTA_RATE'] * 100,
                "to": row_dict_ff['TM_TOV_PCT'] * 100,
                "to_d": row_dict_ff['OPP_TOV_PCT'] * 100,
                "or": row_dict_ff['OREB_PCT'] * 100,
                "or_d": row_dict_ff['OPP_OREB_PCT'] * 100,
                "conf": "NBA" # Generic for now
            }

        if not os.path.exists('data'):
            os.makedirs('data')

        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
            
        print(f"Successfully saved stats for {len(processed_data)} NBA teams to {OUTPUT_FILE}")

    except Exception as e:
        print(f"Error fetching NBA stats: {e}")

if __name__ == "__main__":
    fetch_nba_advanced_stats()
