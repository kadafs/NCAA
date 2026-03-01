import json
import os

leagues_to_add = [
    {"code": "hk_1st", "id": 381, "name": "Hong Kong 1st Division", "country": "Hong-Kong"},
    {"code": "eng_dev_2", "id": 703, "name": "Professional Development League", "country": "England"},
    {"code": "eng_pl_2", "id": 702, "name": "Premier League 2", "country": "England"},
    {"code": "wales_champ", "id": 111, "name": "FAW Championship", "country": "Wales"},
    {"code": "aus_landesliga", "id": 228, "name": "Landesliga Salzburg", "country": "Austria"},
    {"code": "scot_highland", "id": 730, "name": "Highland League", "country": "Scotland"},
    {"code": "scot_lowland", "id": 731, "name": "Lowland League", "country": "Scotland"},
    {"code": "ind_ileague", "id": 324, "name": "I-League", "country": "India"},
    {"code": "cro_1nl", "id": 211, "name": "First NL", "country": "Croatia"},
    {"code": "swe_div1_norra", "id": 563, "name": "Ettan Norra", "country": "Sweden"},
    {"code": "uefa_cl", "id": 2, "name": "UEFA Champions League", "country": "World"},
    {"code": "nor_div1", "id": 104, "name": "1. Division", "country": "Norway"},
    {"code": "den_superliga", "id": 119, "name": "Superliga", "country": "Denmark"},
    {"code": "ger_reg_west", "id": 87, "name": "Regionalliga West", "country": "Germany"},
    {"code": "eng_isthmian", "id": 58, "name": "Isthmian Premier", "country": "England"},
    {"code": "lat_1liga", "id": 364, "name": "1. Liga", "country": "Latvia"},
    {"code": "crc_segunda", "id": 163, "name": "Liga de Ascenso", "country": "Costa-Rica"},
    {"code": "ned_eredivisie", "id": 88, "name": "Eredivisie", "country": "Netherlands"},
    {"code": "scot_prem", "id": 179, "name": "Premiership", "country": "Scotland"},
    {"code": "ban_pl", "id": 398, "name": "Premier League", "country": "Bangladesh"},
    {"code": "tha_pl", "id": 296, "name": "Thai League 1", "country": "Thailand"},
    {"code": "swe_damallsvenskan", "id": 549, "name": "Damallsvenskan", "country": "Sweden"}
]

# High-scoring league template
TEMPLATE = {
    "name": "",
    "league_id": 0,
    "country": "",
    "season": 2024,
    "btts_market_avg": 0.58,  # Slightly higher baseline for these high-scoring leagues
    "btts_edge_threshold": 0.04,
    "draw_edge_threshold": 0.05,
    "regression_factor": 0.80, # Lower regression factor for lower-tier/variance leagues
    "min_games_played": 5,
    "sharp_params": {
        "defensive_btts_drag": -0.05,
        "defensive_draw_boost": 0.02,
        "attacking_btts_boost": 0.06,
        "btts_historical_weight": 0.15,
        "draw_prone_boost": 0.03,
        "form_hot_threshold": 7,
        "form_hot_btts_boost": 0.04,
        "form_cold_threshold": 2,
        "form_cold_btts_drag": -0.03,
        "max_btts_adjustment": 0.15
    }
}

os.makedirs("configs/leagues", exist_ok=True)

for l in leagues_to_add:
    cfg = TEMPLATE.copy()
    cfg["name"] = l["name"]
    cfg["league_id"] = l["id"]
    cfg["country"] = l["country"]
    
    # Adjust big names slightly
    if l["code"] in ["uefa_cl", "den_superliga", "ned_eredivisie", "scot_prem"]:
        cfg["regression_factor"] = 0.85 
        cfg["btts_market_avg"] = 0.55

    out_path = f"configs/leagues/{l['code']}.json"
    with open(out_path, "w") as f:
        json.dump(cfg, f, indent=4)

print(f"Generated {len(leagues_to_add)} config files.")

# Generate the python dict entries for SUPPORTED_LEAGUES
print("\n--- Copy-paste for SUPPORTED_LEAGUES ---")
for l in leagues_to_add:
    print(f'    "{l["code"]}": {{"id": {l["id"]}, "name": "{l["name"]}", "country": "{l["country"]}"}},')

print("\n--- Copy-paste for run_universal.py --league choices ---")
print(", ".join(f"'{l['code']}'" for l in leagues_to_add))
