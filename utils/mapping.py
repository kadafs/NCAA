def clean_team_name(name):
    """
    Standardizes team names by removing common punctuation and formatting.
    """
    if not name: return ""
    # Standardize common abbreviations before general punctuation stripping
    n = name.replace("St.", "State").replace("Fla.", "Florida").replace("Pa.", "Pennsylvania")
    return n.replace(".", "").replace("(", "").replace(")", "").replace(" ", "").replace("'", "").lower()

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
    "stmarysca": "saintmarys",
    "stmarys-ca": "saintmarys",
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
    "ncstate": "northcarolinastate",
    "armypowers": "army",
    "armywestpoint": "army",
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

# EuroLeague Tricode Mapping
EURO_TRICODES = {
    "ALB": "ALBA Berlin",
    "EFS": "Anadolu Efes Istanbul",
    "ASM": "AS Monaco",
    "BKN": "Baskonia Vitoria-Gasteiz",
    "CZV": "Crvena Zvezda Meridianbet Belgrade",
    "MIL": "EA7 Emporio Armani Milan",
    "BAR": "FC Barcelona",
    "BAY": "FC Bayern Munich",
    "FBB": "Fenerbahce Beko Istanbul",
    "ASV": "LDLC ASVEL Villeurbanne",
    "MTA": "Maccabi Playtika Tel Aviv",
    "OLY": "Olympiacos Piraeus",
    "PAO": "Panathinaikos Aktor Athens",
    "PAR": "Paris Basketball",
    "PTZ": "Partizan Mozzart Bet Belgrade",
    "RMB": "Real Madrid",
    "VIR": "Virtus Segafredo Bologna",
    "ZAL": "Zalgiris Kaunas"
}

def get_nba_team_from_tricode(tricode):
    return NBA_TRICODES.get(tricode, tricode)

def get_euro_team_from_tricode(tricode):
    return EURO_TRICODES.get(tricode, tricode)
