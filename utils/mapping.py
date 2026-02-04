import zoneinfo
from datetime import datetime

def get_target_date(date_str=None):
    """
    Returns a datetime object for the target date.
    Accepts 'YYYY-MM-DD'. Defaults to current date in ET with 10PM lookahead.
    """
    et_tz = zoneinfo.ZoneInfo("America/New_York")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=et_tz)
        except ValueError:
            print(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")
    
    now = datetime.now(et_tz)
    # If it's late night in ET (after 10 PM), we probably want tomorrow's games
    if now.hour >= 22:
        from datetime import timedelta
        return now + timedelta(days=1)
    return now

def clean_team_name(name):
    """
    Standardizes team names by removing common punctuation and formatting.
    v1.6.4: Ultimate Normalization (Folding Saint/State -> St).
    """
    if not name: return ""
    import re
    
    # 1. Lowercase and remove punctuation first
    n = name.lower().strip()
    n = n.replace(".", "").replace("(", "").replace(")", "").replace("'", "").replace("-", "").replace("&", "and")
    n = n.replace("@", " ")
    
    # 2. Normalize common separators
    n = re.sub(r'\b(vs\.?|at)\b', ' ', n)
    
    # 3. FOLDING: Normalize all variants of Saint/State to 'st'
    # This works because no D1 team name (other than the word Saint/State) contains these markers correctly as standalone words.
    # We turn "saint marys" -> "st marys" and "iowa state" -> "iowa st"
    n = re.sub(r'\b(saint|state)\b', 'st', n)
    
    # 4. Expand directional/university markers (Safe)
    def expand_safe(n_inner):
        n_inner = re.sub(r'\bmiss\b', 'mississippi', n_inner)
        n_inner = re.sub(r'\bfla\b', 'florida', n_inner)
        n_inner = re.sub(r'\bpa\b', 'pennsylvania', n_inner)
        n_inner = re.sub(r'\bmich\b', 'michigan', n_inner)
        n_inner = re.sub(r'\bwash\b', 'washington', n_inner)
        n_inner = re.sub(r'\bcolo\b', 'colorado', n_inner)
        n_inner = re.sub(r'\bariz\b', 'arizona', n_inner)
        n_inner = re.sub(r'\btenn\b', 'tennessee', n_inner)
        n_inner = re.sub(r'\bga\b', 'georgia', n_inner)
        n_inner = re.sub(r'\bky\b', 'kentucky', n_inner)
        n_inner = re.sub(r'\bill\b', 'illinois', n_inner)
        n_inner = re.sub(r'\bn\b\.', 'north', n_inner)
        n_inner = re.sub(r'\bs\b\.', 'south', n_inner)
        n_inner = re.sub(r'\bmd\b', 'maryland', n_inner)
        n_inner = re.sub(r'\bla\b', 'louisiana', n_inner)
        n_inner = re.sub(r'\bu\b\.', 'university', n_inner)
        n_inner = re.sub(r'\buniv\b', 'university', n_inner)
        return n_inner

    n = expand_safe(n)
    
    # 5. Collapse all characters (Remove all spaces)
    n = n.replace(" ", "")
    
    # 6. Final University logic
    if n.endswith("u") and len(n) > 5:
        n = n[:-1]
    if n.endswith("university") and len(n) > 10:
        n = n[:-10]
        
    return n

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

# Common Basketball Aliases (NBA and NCAA)
# Normalized form (Saint/State -> st) to canonical BARTTORVIK keys
BASKETBALL_ALIASES = {
    # St. Thomas Folded Mapping
    "stthomas": "stthomas",
    "stthomasmn": "stthomas",
    
    # St. Mary's Folded Mapping
    "stmarys": "saintmarys",
    "stmarysca": "saintmarys",
    
    # South Dakota St Folded Mapping
    "southdakotast": "southdakotastate",
    "sdsu": "southdakotastate",
    
    # Other Folded Aliases
    "uconn": "connecticut",
    "olemiss": "mississippi",
    "penn": "pennsylvania",
    "upenn": "pennsylvania",
    "md": "maryland",
    "fiu": "floridainternational",
    "fgcu": "floridagulfcoast",
    "mtsu": "middletennessee",
    "middletenn": "middletennessee",
    "olemiss": "mississippi",
    "uncg": "uncgreensboro",
    "uncw": "uncwilmington",
    "unca": "uncasheville",
    "uncc": "charlotte",
    "upenn": "pennsylvania",
    "penn": "pennsylvania",
    "uconn": "connecticut",
    "umass": "massachusetts",
    "umkc": "kansascity",
    "fdu": "fairleighdickinson",
    "etsu": "easttennesseestate",
    "mtsu": "middletennessee",
    "vcu": "virginiacommonwealth",
    "smu": "southernmethodist",
    "tcu": "texaschristian",
    "byu": "brighamyoung",
    "lsu": "louisianastate",
    "olemississippi": "mississippi",
    "southernmiss": "southernmississippi",
    "usf": "southflorida",
    "ucf": "centralflorida",
    "fau": "floridaatlantic",
    "fiu": "floridainternational",
    "stjohns": "saintjohns",
    "stjosephs": "saintjosephs",
    "stlouis": "saintlouis",
    "stpetes": "saintpeters",
    "stmarys": "saintmarys",
    "statemary": "saintmarys",
    "statemarysca": "saintmarys",
    "loyolachicago": "loyolail",
    "loyolail": "loyolachicago",
    "uic": "illinoischicago",
    "niagara": "niagarauniversity",
    "fullerton": "calstfullerton",
    "longbeachstate": "calstlongbeach",
    "northridge": "calstnorthridge",
    "bakersfield": "calstbakersfield",
    "uapb": "arkansaspinebluff",
    "uncg": "uncgreensboro",
    "unca": "uncasheville",
    "uncw": "uncwilmington",
    "uncc": "charlotte",
    "louisiana": "louisianalafayette",
    "ulm": "louisianamonroe",
    "stmarys": "saintmarys",
    "statemarys": "saintmarys",
    "stthomas": "stthomasmn",
    "statethomas": "stthomasmn",
    "saintthomas": "stthomasmn",
    "armywestpoint": "army",
    "armyblackknights": "army",
    "fiu": "floridainternational",
    "fau": "floridaatlantic",
    "ucf": "centralflorida",
    "usf": "southflorida",
    "olemiss": "mississippi",
    "olemississippi": "mississippi",
    "southernmiss": "southernmississippi",
    "md": "maryland",
    "mtsu": "middletennessee",
    "middletenn": "middletennessee",
    "loyolamd": "loyolamaryland",
    "loyolamaryland": "loyolamd",
    "utmartin": "tennesseemartin",
    "tennesseemartin": "utmartin",
    "utrgv": "utriograndevalley",
    "utriograndevalley": "texasriograndevalley",
    "texasriograndevalley": "utriograndevalley",
    "westernky": "westernkentucky",
    "omaha": "nebraskaomaha",
    "littlerock": "arkansaslittlerock",
    "arkansaslittlerock": "littlerock",
    "aandmcorpuschristi": "texasaandmcc",
    "texasaandmcc": "aandmcorpuschristi",
    "ncstate": "northcarolinastate",
    "usc": "southerncalifornia",
    "southerncal": "southerncalifornia",
    "scupstatespartans": "uscupstate",
    "uscupstatespartans": "uscupstate",
    "moreheadstateeagles": "moreheadstate",
    "moreheadsteagles": "moreheadstate",
    "utmartinskyhawks": "tennesseemartin",
    "tennesseemartinskyhawks": "tennesseemartin",
    "easternillinoispanthers": "easternillinois",
    "ualbany": "albany",
    "albanygreatdanes": "albany",
    "njithighlanders": "njit",
    "samfordbulldogs": "samford",
    "furmanpaladins": "furman",
    "loyolachicago": "loyolail",
    "loyolail": "loyolachicago",
    "stlouis": "saintlouis",
    "statelouis": "saintlouis",
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
    "MTA": "Maccabi Rapyd Tel Aviv",
    "OLY": "Olympiacos Piraeus",
    "PAO": "Panathinaikos AKTOR Athens",
    "PAR": "Paris Basketball",
    "DUB": "Dubai Basketball",
    "PTZ": "Partizan Mozzart Bet Belgrade",
    "RMB": "Real Madrid",
    "VIR": "Virtus Bologna",
    "ZAL": "Zalgiris Kaunas"
}

# EuroCup Tricode Mapping (v2.0)
EUROCUP_TRICODES = {
    "PAM": "Valencia Basket",
    "JER": "Hapoel Jerusalem Basketball Club",
    "TTK": "Turk Telekom Ankara",
    "LJU": "KK Cedevita Olimpija",
    "RED": "Crvena Zvezda Meridianbet Belgrade",
    "PAR": "Partizan Mozzart Bet Belgrade",
    "ULM": "ratiopharm ulm",
    "JOV": "Club Joventut Badalona",
    "CAN": "Club Baloncesto Gran Canaria",
    "UNK": "UNICS Kazan",
    "KHI": "BC Khimki",
    "TIV": "Lokomotiv Kuban",
    "MAL": "Unicaja Malaga",
    "HTA": "Hapoel Tel Aviv",
    "BOU": "JL Bourg",
    "CLU": "U-BT Cluj-Napoca",
    "ANR": "MoraBanc Andorra",
    "BIL": "Bilbao Basket",
    "VNC": "Umana Reyer Venice",
    "TRN": "Dolomiti Energia Trento"
}

# NBL Tricode Mapping (v3.0)
NBL_TRICODES = {
    "ADE": "Adelaide 36ers",
    "BRI": "Brisbane Bullets",
    "CNS": "Cairns Taipans",
    "ILL": "Illawarra Hawks",
    "MEL": "Melbourne United",
    "NZB": "New Zealand Breakers",
    "PER": "Perth Wildcats",
    "SEM": "South East Melbourne Phoenix",
    "SYD": "Sydney Kings",
    "TAS": "Tasmania JackJumpers"
}

# ACB Tricode Mapping (v3.0)
ACB_TRICODES = {
    "BAR": "FC Barcelona",
    "RMB": "Real Madrid",
    "UNI": "Unicaja",
    "VBC": "Valencia Basket",
    "JOV": "Joventut Badalona",
    "GCA": "Dreamland Gran Canaria",
    "BAS": "Baskonia",
    "UCAM": "UCAM Murcia",
    "TEN": "Lenovo Tenerife",
    "BAX": "BAXI Manresa",
    "MAO": "MoraBanc Andorra",
    "CAS": "Casademont Zaragoza",
    "BIL": "Surne Bilbao Basket",
    "GIR": "Bàsquet Girona",
    "BRE": "Río Breogán",
    "COV": "Coviran Granada",
    "LLD": "Hiopos Lleida",
    "COR": "Leyma Coruña"
}

def get_nba_team_from_tricode(tricode):
    return NBA_TRICODES.get(tricode, tricode)

def get_euro_team_from_tricode(tricode):
    return EURO_TRICODES.get(tricode, tricode)

def get_eurocup_team_from_tricode(tricode):
    return EUROCUP_TRICODES.get(tricode, tricode)

def get_nbl_team_from_tricode(tricode):
    return NBL_TRICODES.get(tricode, tricode)

def get_acb_team_from_tricode(tricode):
    return ACB_TRICODES.get(tricode, tricode)
