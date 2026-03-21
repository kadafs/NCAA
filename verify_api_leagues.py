import os
import json
import requests
from dotenv import load_dotenv
from difflib import get_close_matches

load_dotenv()

API_KEY = os.getenv("API_BASKETBALL_KEY")
BASE_URL = "https://v1.basketball.api-sports.io/leagues"
HEADERS = {"x-apisports-key": API_KEY}

SKIPPED_SLUGS = [
    "belarus_premier_league_women", "brazil_lbf_women", "chile_lnb_2_2025", 
    "czech_republic_zbl_women", "denmark_kvindebasketligaen_women", 
    "europe_latvian_estonian_league", "finland_korisliiga_women", 
    "hungary_nb_i_a_women", "iceland_premier_league_women", 
    "indonesia_ibl", "ireland_superleague", "lithuania_moteru_lyga_women",
    "luxembourg_lbbl_women", "north_macedonia_prva_liga_women", 
    "poland_basket_liga_women", "romania_liga_national_women", 
    "russia_premier_league_women", "slovakia_extraliga_women", 
    "south_korea_wkbl_women", "spain_liga_femenina_women", 
    "sweden_basketettan_women", "sweden_basketligan",
    "switzerland_sb_league_women", "taiwan_p_league", 
    "ukraine_fbu_superleague", "ukraine_superleague_women",
    "vtb_united_league", "adidas-next-generation-tournament",
    "adriatic-junior-aba-league", "basketball-africa-league"
]

def verify():
    print(f"Fetching master league list from API-Basketball...")
    response = requests.get(BASE_URL, headers=HEADERS)
    data = response.json()
    
    if data.get("errors"):
        print(f"ERROR: {data['errors']}")
        return

    api_leagues = data.get("response", [])
    print(f"Retrieved {len(api_leagues)} total leagues from API.\n")

    # Create simplified search index
    # [ (name, country, id) ]
    search_index = []
    for l in api_leagues:
        name = l["name"]
        country = l["country"]["name"]
        lid = l["id"]
        search_index.append((f"{country} {name}".lower(), lid, name, country))

    matches_found = []

    print(f"{'SLUG':<40} | {'MATCH':<30} | {'ID':<5}")
    print("-" * 80)

    for slug in SKIPPED_SLUGS:
        clean_slug = slug.replace("_", " ").replace("-", " ").lower()
        
        # Try direct match or close match
        best_match = None
        best_lid = None
        
        # 1. Look for direct keyword overlap
        for full_text, lid, name, country in search_index:
            if clean_slug in full_text or full_text in clean_slug:
                best_match = f"{country} {name}"
                best_lid = lid
                break
        
        # 2. If no direct match, try difflib
        if not best_match:
            names_only = [x[0] for x in search_index]
            close = get_close_matches(clean_slug, names_only, n=1, cutoff=0.7)
            if close:
                match_text = close[0]
                idx = names_only.index(match_text)
                best_match = f"{search_index[idx][3]} {search_index[idx][2]}"
                best_lid = search_index[idx][1]

        if best_match:
            print(f"{slug:<40} | {best_match:<30} | {best_lid:<5}")
            matches_found.append((slug, best_lid))
        else:
            print(f"{slug:<40} | NO MATCH FOUND             | ---")

    if matches_found:
        print(f"\nFound {len(matches_found)} potential mappings.")
        print("To apply these, add them to data/league_slug_map.json")
    else:
        print("\nNo new matches found.")

if __name__ == "__main__":
    verify()
