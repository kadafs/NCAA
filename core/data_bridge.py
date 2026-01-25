# Universal DataBridge v1.4
import os
import json
import sys

# Root addition for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.mapping import find_team_in_dict, BASKETBALL_ALIASES, NBA_TRICODES

class UniversalDataBridge:
    """
    Bridges raw data files into standardized engine inputs.
    """
    
    def __init__(self, league_name):
        self.league = league_name.upper()
        self.data_dir = "data"

    def _load_json(self, filename):
        path = os.path.join(self.data_dir, filename)
        if not os.path.exists(path): return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_standardized_sheet(self, date_obj=None):
        """Dispatches to league-specific population logic."""
        if self.league == "NBA":
            return self._pop_nba()
        elif self.league == "NCAA":
            return self._pop_ncaa(date_obj=date_obj)
        elif self.league == "EURO":
            return self._pop_euro()
        elif self.league == "EUROCUP":
            return self._pop_eurocup()
        elif self.league == "NBL":
            return self._pop_nbl()
        elif self.league == "ACB":
            return self._pop_acb()
        else:
            return []

    def _pop_nba(self):
        """NBA-specific population logic moved to core."""
        matchups = self._load_json("nba_matchups.json")
        all_stats = self._load_json("nba_stats.json")
        
        daily_sheet = []
        for m in matchups:
            teamA_name = find_team_in_dict(m['away'], all_stats, BASKETBALL_ALIASES)
            teamH_name = find_team_in_dict(m['home'], all_stats, BASKETBALL_ALIASES)
            
            if not teamA_name or not teamH_name: continue
            
            sA = all_stats[teamA_name]
            sH = all_stats[teamH_name]

            # NBA ESPN logo mapping
            triA = [k for k, v in NBA_TRICODES.items() if v == teamA_name][0] if teamA_name in NBA_TRICODES.values() else "NBA"
            triH = [k for k, v in NBA_TRICODES.items() if v == teamH_name][0] if teamH_name in NBA_TRICODES.values() else "NBA"
            
            daily_sheet.append({
                "team": teamA_name,
                "opponent": teamH_name,
                "away_details": {
                    "name": teamA_name,
                    "code": triA,
                    "logo": f"https://a.espncdn.com/i/teamlogos/nba/500/{triA.lower()}.png"
                },
                "home_details": {
                    "name": teamH_name,
                    "code": triH,
                    "logo": f"https://a.espncdn.com/i/teamlogos/nba/500/{triH.lower()}.png"
                },
                "pace_adjustment": (sA['adj_t'] + sH['adj_t']) / 2,
                "efficiency_adjustment": (sA['adj_off'] + sH['adj_def'] + sH['adj_off'] + sA['adj_def']) / 4,
                "market_total": m.get('total', 230.5),
                "is_elite_offense": sA['adj_off'] > 120 or sH['adj_off'] > 120,
                "is_strong_defense": sA['adj_def'] < 110 or sH['adj_def'] < 110,
                "three_pa_total": sA.get('fg3a', 35) + sH.get('fg3a', 35),
                "statsA": {
                    "adj_off": sA['adj_off'],
                    "adj_def": sA['adj_def'],
                    "adj_t": sA['adj_t'],
                    "four_factors": sA.get('four_factors', {})
                },
                "statsH": {
                    "adj_off": sH['adj_off'],
                    "adj_def": sH['adj_def'],
                    "adj_t": sH['adj_t'],
                    "four_factors": sH.get('four_factors', {})
                }
            })
        return daily_sheet

    def _pop_ncaa(self, date_obj=None):
        """NCAA-specific population logic moved to core."""
        bt_data = self._load_json("barttorvik_stats.json")
        
        from ncaa.v1_2.populate import get_daily_input_sheet
        daily_sheet = get_daily_input_sheet(date_obj=date_obj)
        
        processed_sheet = []
        for d in daily_sheet:
            teamA_bt = find_team_in_dict(d['team'], bt_data, BASKETBALL_ALIASES)
            teamH_bt = find_team_in_dict(d['opponent'], bt_data, BASKETBALL_ALIASES)
            
            sA = bt_data.get(teamA_bt, {})
            sH = bt_data.get(teamH_bt, {})

            # Logo strategy for NCAA could vary, often requires more complex mapping
            # We'll use a placeholder or best-effort short name
            
            processed_sheet.append({
                **d,
                "away_details": {
                    "name": teamA_bt or d['team'],
                    "code": d['team'][:4].upper(),
                    "logo": ""
                },
                "home_details": {
                    "name": teamH_bt or d['opponent'],
                    "code": d['opponent'][:4].upper(),
                    "logo": ""
                },
                "statsA": {
                    "adj_off": sA.get('adj_off', 110.0),
                    "adj_def": sA.get('adj_def', 110.0),
                    "adj_t": sA.get('adj_t', 70.0),
                    "four_factors": {"efg": sA.get('efg', 0), "tov": sA.get('to', 0), "orb": sA.get('or', 0), "ftr": sA.get('ftr', 0)}
                },
                "statsH": {
                    "adj_off": sH.get('adj_off', 110.0),
                    "adj_def": sH.get('adj_def', 110.0),
                    "adj_t": sH.get('adj_t', 70.0),
                    "four_factors": {"efg": sH.get('efg', 0), "tov": sH.get('to', 0), "orb": sH.get('or', 0), "ftr": sH.get('ftr', 0)}
                }
            })
        return processed_sheet

    def _pop_euro(self):
        """EuroLeague-specific population logic v1.9."""
        matchups = self._load_json("euro_matchups.json")
        all_stats = self._load_json("euro_stats.json")
        
        daily_sheet = []
        for m in matchups:
            teamA_name = find_team_in_dict(m['away'], all_stats)
            teamH_name = find_team_in_dict(m['home'], all_stats)
            
            if not teamA_name or not teamH_name: continue
            
            sA = all_stats[teamA_name]
            sH = all_stats[teamH_name]
            
            daily_sheet.append({
                "team": teamA_name,
                "opponent": teamH_name,
                "pace_adjustment": (sA.get('adj_t', 72.0) + sH.get('adj_t', 72.0)) / 2,
                "efficiency_adjustment": (
                    sA.get('adj_off', 110.0) + sH.get('adj_def', 110.0) +
                    sH.get('adj_off', 110.0) + sA.get('adj_def', 110.0)
                ) / 4,
                "market_total": m.get('total', 160.0),
                "is_elite_offense": sA.get('adj_off', 110.0) > 120 or sH.get('adj_off', 110.0) > 120,
                "is_strong_defense": sA.get('adj_def', 110.0) < 105 or sH.get('adj_def', 110.0) < 105,
                "three_pa_total": sA.get('fg3a', 25.0) + sH.get('fg3a', 25.0),
                "statsA": {
                    "adj_off": sA.get('adj_off', 110.0),
                    "adj_def": sA.get('adj_def', 110.0),
                    "adj_t": sA.get('adj_t', 72.0)
                },
                "statsH": {
                    "adj_off": sH.get('adj_off', 110.0),
                    "adj_def": sH.get('adj_def', 110.0),
                    "adj_t": sH.get('adj_t', 72.0)
                }
            })
        return daily_sheet

    def _pop_eurocup(self):
        """EuroCup-specific population logic v2.0."""
        matchups = self._load_json("eurocup_matchups.json")
        all_stats = self._load_json("eurocup_stats.json")
        
        daily_sheet = []
        for m in matchups:
            teamA_name = find_team_in_dict(m['away'], all_stats)
            teamH_name = find_team_in_dict(m['home'], all_stats)
            
            if not teamA_name or not teamH_name: continue
            
            sA = all_stats[teamA_name]
            sH = all_stats[teamH_name]
            
            # EuroCup Pivots (Researched)
            pivot_pace = 74.5
            pivot_eff = 110.8
            
            daily_sheet.append({
                "team": teamA_name,
                "opponent": teamH_name,
                "pace_adjustment": (sA.get('adj_t', pivot_pace) + sH.get('adj_t', pivot_pace)) / 2,
                "efficiency_adjustment": (
                    sA.get('adj_off', pivot_eff) + sH.get('adj_def', pivot_eff) +
                    sH.get('adj_off', pivot_eff) + sA.get('adj_def', pivot_eff)
                ) / 4,
                "market_total": m.get('total', 165.0),
                "is_elite_offense": sA.get('adj_off', pivot_eff) > (pivot_eff * 1.05),
                "is_strong_defense": sA.get('adj_def', pivot_eff) < (pivot_eff * 0.95),
                "three_pa_total": sA.get('fg3a', 25.0) + sH.get('fg3a', 25.0),
                "statsA": {
                    "adj_off": sA.get('adj_off', pivot_eff),
                    "adj_def": sA.get('adj_def', pivot_eff),
                    "adj_t": sA.get('adj_t', pivot_pace),
                    "four_factors": sA.get('four_factors', {})
                },
                "statsH": {
                    "adj_off": sH.get('adj_off', pivot_eff),
                    "adj_def": sH.get('adj_def', pivot_eff),
                    "adj_t": sH.get('adj_t', pivot_pace),
                    "four_factors": sH.get('four_factors', {})
                }
            })
        return daily_sheet

    def _pop_nbl(self):
        """NBL-specific population logic v3.0."""
        from nbl.v1_2.populate import get_daily_input_sheet
        return get_daily_input_sheet()

    def _pop_acb(self):
        """ACB-specific population logic v3.0."""
        from acb.v1_2.populate import get_daily_input_sheet
        return get_daily_input_sheet()
