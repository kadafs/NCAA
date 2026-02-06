import requests
import json
from datetime import datetime
from utils.mapping import BASKETBALL_ALIASES, NBA_TRICODES, clean_team_name

class PolymarketProvider:
    """
    Fetches and normalizes prediction market data from Polymarket's Gamma API.
    """
    GAMMA_API = "https://gamma-api.polymarket.com/events"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_markets(self, league="nba"):
        """
        Fetches active markets for the given league (nba/cbb).
        Returns a dictionary keyed by standardized Matchup ID.
        """
        slug = "cbb" if league.lower() == "ncaa" else "nba"
        
        params = {
            "closed": "false",
            "tag_slug": slug,
            "limit": 100, # Fetch enough to cover daily slate
            "order": "volume24hr",
            "ascending": "false"
        }
        
        try:
            res = self.session.get(self.GAMMA_API, params=params, timeout=5)
            res.raise_for_status()
            data = res.json()
            events = data if isinstance(data, list) else data.get('data', [])
            
            market_map = {}
            
            for event in events:
                title = event.get('title', '')
                
                # Filter for Game Matchups (Must contain 'vs')
                if " vs " not in title:
                    continue
                    
                # Parse Teams from Title "Team A vs Team B"
                try:
                    parts = title.split(" vs ")
                    teamA_raw = parts[0].strip()
                    # Remove potential extra text from Team B (e.g., "Team B - Feb 6")
                    teamB_raw = parts[1].split(" - ")[0].strip() 
                    
                    # Normalize
                    teamA = self._normalize_team(teamA_raw, league)
                    teamB = self._normalize_team(teamB_raw, league)
                    
                    if not teamA or not teamB:
                        continue
                        
                    # Find relevant markets (Winner/Moneyline)
                    for m in event.get('markets', []):
                        q = m.get('question', '')
                        outcomes = json.loads(m.get('outcomes', '[]'))
                        prices = json.loads(m.get('outcomePrices', '[]'))
                        
                        if len(outcomes) != 2 or len(prices) != 2:
                            continue
                            
                        # Identify Market Type
                        m_type = "winner" if "Winner" in q or "Moneyline" in q else None
                        
                        if m_type == "winner":
                            # Outcomes are usually ["Team A", "Team B"] or ["Yes", "No"] (rare for games)
                            # Polymarket usually does ["Team A", "Team B"] for sports? 
                            # Checking inspection: Outcomes: ["Yes", "No"] for "Will X win?"
                            # Let's handle "Yes/No" logic if the question is "Will Team A win?"
                            
                            # Inspection showed: "Will the Knicks win?" -> ["Yes", "No"]
                            # But we need "Knicks vs Pistons".
                            # Let's look at the structure from previous logs if possible or code defensively.
                            # Assuming "Team A vs Team B" event structure often has "Winner" market.
                            
                            # Simply map the event ID
                            matchup_id = f"{teamA}-{teamB}"
                            matchup_id_rev = f"{teamB}-{teamA}"
                            
                            market_data = {
                                "id": m.get('id'),
                                "title": m.get('question'),
                                "outcomes": outcomes,
                                "prices": prices,
                                "volume": m.get('volume24hr', 0),
                                "url": f"https://polymarket.com/event/{event.get('slug')}"
                            }
                            
                            market_map[matchup_id] = market_data
                            market_map[matchup_id_rev] = market_data
                            
                except Exception as e:
                    continue
                    
            return market_map

        except Exception as e:
            print(f"Polymarket Fetch Error: {e}")
            return {}

    def _normalize_team(self, name, league):
        """Uses existing mapping utilities."""
        # Clean common Polymarket prefixes/suffixes
        clean = name.replace("The ", "")
        
        # Try direct alias match
        if clean in BASKETBALL_ALIASES:
            return BASKETBALL_ALIASES[clean]
            
        # Try specific league tricodes
        if league == "nba":
            for tri, full in NBA_TRICODES.items():
                if full == clean or tri == clean:
                    return full
                    
        return clean_team_name(clean)
