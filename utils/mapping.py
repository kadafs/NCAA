import zoneinfo
from datetime import datetime

def get_target_date(date_str=None):
    """
    Returns a datetime object for the target date.
    Accepts 'YYYY-MM-DD'. Defaults to current date in ET.
    """
    et_tz = zoneinfo.ZoneInfo("America/New_York")
    if date_str:
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=et_tz)
        except ValueError:
            print(f"Invalid date format: {date_str}. Expected YYYY-MM-DD.")
    return datetime.now(et_tz)

def clean_team_name(name):
    """
    Standardizes team names by removing common punctuation and formatting.
    """
    if not name: return ""
    import re
    # 1. Expand common abbreviations
    n = name.replace("St.", "State").replace("Fla.", "Florida").replace("Pa.", "Pennsylvania")
    n = n.replace("Mich.", "Michigan").replace("Wash.", "Washington").replace("Colo.", "Colorado")
    n = n.replace("Ariz.", "Arizona").replace("Tenn.", "Tennessee").replace("Ga.", "Georgia")
    n = n.replace("Ky.", "Kentucky").replace("Ill.", "Illinois").replace("Miss.", "Mississippi")
    n = n.replace("N.", "North").replace("S.", "South").replace("E.", "East").replace("W.", "West")
    n = n.replace("App.", "Appalachian").replace("Ark.", "Arkansas").replace("Atl.", "Atlantic")
    n = n.replace("Car.", "Carolina").replace("Cent.", "Central").replace("Geo.", "Georgia")
    n = n.replace("Mass.", "Massachusetts").replace("Md.", "Maryland")
    
    # 2. General cleaning (punctuation, case, spaces)
    n = n.replace(".", "").replace("(", "").replace(")", "").replace(" ", "").replace("'", "")
    n = n.replace("-", "").replace("&", "and").lower()
    
    # 3. Strip trailing 'u' or 'university' if it's there (often inconsistent)
    if n.endswith("u") and len(n) > 4:
        n = n[:-1]
    if n.endswith("university"):
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
    "ark-pinebluff": "arkansaspinebluff",
    "bethune-cookman": "bethunecookman",
    "csubakersfield": "calstatebakersfield",
    "csun": "calstatenorthridge",
    "centralconnstate": "centralconnecticut",
    "etsu": "easttennesseestate",
    "easternky": "easternkentucky",
    "fdu": "fairleighdickinson",
    "fgcu": "floridagulfcoast",
    "gardner-webb": "gardnerwebb",
    "lmuca": "loyolamarymount",
    "nca&t": "northcarolinaa&t",
    "nccentral": "northcarolinacentral",
    "niu": "northernillinois",
    "northernky": "northernkentucky",
    "sfa": "stephenfaustin",
    "southeastmostate": "southeastmissouristate",
    "southeasternla": "southeasternlouisiana",
    "uic": "illinoischicago",
    "uiw": "incarnateword",
    "ulm": "louisianamonroe",
    "umes": "marylandeasternshore",
    "utmartin": "tennesseemartin",
    "utrgv": "utriograndevalley",
    "westernky": "westernkentucky",
    "omaha": "nebraskaomaha",
    "iuindy": "iuindy",
    "amcorpuschristi": "texasamcorpuschris",
    "little-rock": "arkansaslittlerock",
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
