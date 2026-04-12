import json, sys, difflib
sys.stdout.reconfigure(encoding='utf-8')

# The teams that failed to match
failed_games = [
    (71, "Polonia Warszawa", "Spojnia Stargard"),
    (198, "KK Bosna", "Igokea"),
    (117, "Basket Zaragoza", "Forca Lleida"),
    (40, "Jena", "Wurzburg"),
    (368, "Spirou Charleroi", "Donar Groningen"),
    (368, "BAL Weert", "Oostende"),
    (368, "LWD Basket", "Mechelen"),
    (368, "Belfius Mons", "Zwolle"),
    (85, "Mladost Zemun", "Sloga"),
    (85, "Vojvodina Novi Sad", "Borac Zemun"),
    (85, "Vrsac", "OKK Beograd"),
    (10, "La Roche W", "Lyon W"),
    (10, "Landes W", "Chartres W"),
    (60, "Juventus", "Jonava"),
    (52, "Reggiana", "Cremona"),
    (46, "Kaposvari", "Atomeromu Paks"),
    (46, "Kecskemeti TE", "Kormend"),
    (46, "Szedeak", "DEAC"),
    (32, "Srsni Pisek", "Nymburk"),
    (32, "USK Prague", "Slavia Prague"),
    (111, "Grodno GrSU", "Gomel"),
    (111, "Borisfen 2", "Rubon II"),
    (122, "Al Manama", "Al Muharraq"),
    (95, "Leyma Coruna", "Obradoiro CAB"),
    (95, "Ourense", "Estela"),
    (42, "Artland", "Tubingen"),
    (42, "Paderborn", "Crailsheim Merlins"),
    (123, "Donji Vakuf - Promo", "Mrkonjic Grad"),
    (96, "Sol Girones Bisbal", "Huesca"),
    (96, "Gandia", "Molina Basket"),
    (96, "CB Getafe", "Lliria"),
    (96, "Caceres", "CBC Valladolid"),
    (217, "St. Polten", "BBC Nord"),
    (275, "Trotamundos", "Brillantes"),
    (275, "Marinos", "Diablos")
]

leagues_to_load = set(lid for lid,_,_ in failed_games)

matrix_teams = {}
for lid in leagues_to_load:
    try:
        d = json.load(open(f'data/bball_stats_{lid}_adv.json', encoding='utf-8'))
        matrix_teams[lid] = [t['team_name'] for t in d.get('teams', [])]
    except:
        matrix_teams[lid] = []

mapped_overrides = {}

for lid, home, away in failed_games:
    teams_in_matrix = matrix_teams.get(lid, [])
    if not teams_in_matrix:
        continue # Entire matrix missing (e.g. Chile LNB)
        
    for name in (home, away):
        if name in teams_in_matrix:
            continue
        # Find best match
        matches = difflib.get_close_matches(name.lower(), [t.lower() for t in teams_in_matrix], n=1, cutoff=0.3)
        if matches:
            best_match_lower = matches[0]
            best_match_actual = next(t for t in teams_in_matrix if t.lower() == best_match_lower)
            print(f'"{name}": "{best_match_actual}",  // from {lid}')
        else:
            print(f'// "{name}": ??? (no good matches in {lid})')
