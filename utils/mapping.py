def clean_team_name(name):
    """
    Standardizes team names by removing common punctuation and formatting.
    """
    if not name: return ""
    return name.replace("St.", "State").replace(".", "").replace("(", "").replace(")", "").replace(" ", "").replace("'", "").lower()

def find_team_in_dict(name, target_dict, aliases=None):
    """
    Finds a team name in a dictionary using cleaning, aliases, and substring matching.
    """
    if not name or not target_dict: return None
    if name in target_dict: return name
    
    name_clean = clean_team_name(name)
    
    # 1. Try exact clean match
    for t_name in target_dict:
        if clean_team_name(t_name) == name_clean:
            return t_name
            
    # 2. Check aliases
    if aliases and name_clean in aliases:
        target = aliases[name_clean]
        for t_name in target_dict:
            if clean_team_name(t_name) == target:
                return t_name
                
    # 3. Substring match
    for t_name in target_dict:
        t_clean = clean_team_name(t_name)
        if name_clean in t_clean or t_clean in name_clean:
            return t_name
            
    return None

# Common Basketball Aliases (NBA and NCAA sharing some patterns)
BASKETBALL_ALIASES = {
    "uconn": "connecticut",
    "olemiss": "mississippi",
    "penn": "pennsylvania",
    "upenn": "pennsylvania",
    "stmarys": "saintmarys",
    "umkc": "kansascity",
    "fullerton": "calstfullerton",
    "longbeachstate": "calstlongbeach",
    "northridge": "calstnorthridge",
    "bakersfield": "calstbakersfield",
    "stthomasmn": "stthomas",
    "ulmonroe": "louisianamonroe",
    "louisiana": "louisianalafayette",
    "appstate": "appalachianstate",
    "westerncaro": "westerncarolina",
    "southerncaro": "southcarolina",
    "eastcaro": "eastcarolina",
    "coastalcaro": "coastalcarolina",
}
# NBA Tricode Mapping
NBA_TRICODES = {
    "ATL": "Atlanta Hawks", "BOS": "Boston Celtics", "BKN": "Brooklyn Nets",
    "CHA": "Charlotte Hornets", "CHI": "Chicago Bulls", "CLE": "Cleveland Cavaliers",
    "DAL": "Dallas Mavericks", "DEN": "Denver Nuggets", "DET": "Detroit Pistons",
    "GSW": "Golden State Warriors", "HOU": "Houston Rockets", "IND": "Indiana Pacers",
    "LAC": "LA Clippers", "LAL": "Los Angeles Lakers", "MEM": "Memphis Grizzlies",
    "MIA": "Miami Heat", "MIL": "Milwaukee Bucks", "MIN": "Minnesota Timberwolves",
    "NOP": "New Orleans Pelicans", "NYK": "New York Knicks", "OKC": "Oklahoma City Thunder",
    "ORL": "Orlando Magic", "PHI": "Philadelphia 76ers", "PHX": "Phoenix Suns",
    "POR": "Portland Trail Blazers", "SAC": "Sacramento Kings", "SAS": "San Antonio Spurs",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "WAS": "Washington Wizards"
}

def get_nba_team_from_tricode(tricode):
    return NBA_TRICODES.get(tricode, tricode)
