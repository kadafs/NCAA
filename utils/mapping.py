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
    v1.6.3: Collapsed-form matching (no regex expansion).
    """
    if not name: return ""
    import re
    
    # 1. Strip separators and common filler words
    n = re.sub(r'\b(vs\.?|at|gaels|toreros|tommies|jackrabbits|panthers|raiders|blue raiders|greyhounds|thundering herd|golden eagles|black knights)\b', ' ', name, flags=re.I)
    n = n.replace("@", " ")
    
    # 2. Expand ONLY state/direction abbreviations (Safe)
    def expand_safe(n_inner):
        n_inner = re.sub(r'\bMiss\b', 'Mississippi', n_inner, flags=re.I)
        n_inner = re.sub(r'\bFla\b', 'Florida', n_inner, flags=re.I)
        n_inner = re.sub(r'\bPa\b', 'Pennsylvania', n_inner, flags=re.I)
        n_inner = re.sub(r'\bMich\b', 'Michigan', n_inner, flags=re.I)
        n_inner = re.sub(r'\bWash\b', 'Washington', n_inner, flags=re.I)
        n_inner = re.sub(r'\bColo\b', 'Colorado', n_inner, flags=re.I)
        n_inner = re.sub(r'\bAriz\b', 'Arizona', n_inner, flags=re.I)
        n_inner = re.sub(r'\bTenn\b', 'Tennessee', n_inner, flags=re.I)
        n_inner = re.sub(r'\bGa\b', 'Georgia', n_inner, flags=re.I)
        n_inner = re.sub(r'\bKy\b', 'Kentucky', n_inner, flags=re.I)
        n_inner = re.sub(r'\bIll\b', 'Illinois', n_inner, flags=re.I)
        n_inner = re.sub(r'\bN\b\.', 'North', n_inner, flags=re.I)
        n_inner = re.sub(r'\bS\b\.', 'South', n_inner, flags=re.I)
        n_inner = re.sub(r'\bE\b\.', 'East', n_inner, flags=re.I)
        n_inner = re.sub(r'\bW\b\.', 'West', n_inner, flags=re.I)
        n_inner = re.sub(r'\bMd\b', 'Maryland', n_inner, flags=re.I)
        n_inner = re.sub(r'\bLa\b', 'Louisiana', n_inner, flags=re.I)
        n_inner = re.sub(r'\bU\b\.', 'University', n_inner, flags=re.I)
        n_inner = re.sub(r'\bUniv\b', 'University', n_inner, flags=re.I)
        return n_inner

    n = expand_safe(n)
    
    # Handle specific complex expansions
    n = n.replace("UT Martin", "Tennessee Martin").replace("UT-Martin", "Tennessee Martin")
    n = n.replace("UT ", "Texas ").replace("UMES", "Maryland Eastern Shore")
    n = n.replace("A&M CC", "Texas A&M Corpus Christi").replace("SIU-", "Southern Illinois ")
    n = n.replace("A&M-CC", "Texas A&M Corpus Christi")
    n = n.replace("UIW", "Incarnate Word").replace("FIU", "Florida International")
    
    # 3. Collapse Form (Remove all spaces/punctuation/St expansion)
    n = n.replace(".", "").replace("(", "").replace(")", "").replace(" ", "").replace("'", "")
    n = n.replace("-", "").replace("&", "and").lower()
    
    # 4. Strip trailing 'u' or 'university'
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
# Map collapsed forms (no spaces/no expansion) to canonical BARTTORVIK keys or desired names
BASKETBALL_ALIASES = {
    # St. Thomas Collapsed Mapping
    "stthomas": "stthomas",
    "saintthomas": "stthomas",
    "stthomasmn": "stthomas",
    "saintthomasmn": "stthomas",
    
    # St. Mary's Collapsed Mapping
    "stmarys": "saintmarys",
    "saintmarys": "saintmarys",
    "stmarys-ca": "saintmarys",
    "stmarysca": "saintmarys",
    "saintmary": "saintmarys",
    
    # South Dakota St Collapsed Mapping
    "southdakotast": "southdakotastate",
    "southdakotastate": "southdakotastate",
    "sdsu": "southdakotastate",
    
    # Other Collapsed Aliases
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
    "fiu": "floridainternational",
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
    "fgcu": "florigulfcoast",
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
