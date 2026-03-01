import json
import os

leagues_to_add = [
    {"code": "par_primera_ap", "id": 250, "name": "Division Profesional Apertura", "country": "Paraguay"},
    {"code": "usa_mls", "id": 253, "name": "Major League Soccer", "country": "USA"},
    {"code": "ven_primera", "id": 299, "name": "Primera Division", "country": "Venezuela"},
    {"code": "spa_tercera_6", "id": 444, "name": "Tercera RFEF Group 6", "country": "Spain"},
    {"code": "hon_liga_nac", "id": 234, "name": "Liga Nacional", "country": "Honduras"},
    {"code": "spa_tercera_18", "id": 456, "name": "Tercera RFEF Group 18", "country": "Spain"},
    {"code": "ecu_primera_b", "id": 243, "name": "Liga Pro Serie B", "country": "Ecuador"},
    {"code": "arg_nacional_b", "id": 129, "name": "Primera Nacional", "country": "Argentina"},
    {"code": "arg_primera", "id": 128, "name": "Liga Profesional", "country": "Argentina"},
    {"code": "ita_serie_b", "id": 136, "name": "Serie B", "country": "Italy"},
    {"code": "col_primera_a", "id": 239, "name": "Primera A", "country": "Colombia"},
    {"code": "arg_primera_b", "id": 131, "name": "Primera B Metropolitana", "country": "Argentina"},
    {"code": "fra_national", "id": 63, "name": "National 1", "country": "France"},
    {"code": "egy_prem", "id": 233, "name": "Premier League", "country": "Egypt"},
    {"code": "uru_apertura", "id": 268, "name": "Primera Div Apertura", "country": "Uruguay"}
]

# High-draw league template
TEMPLATE = {
    "name": "",
    "league_id": 0,
    "country": "",
    "season": 2024,
    "btts_market_avg": 0.48,  # Lower BTTS average correlates with higher draw chance
    "btts_edge_threshold": 0.04,
    "draw_edge_threshold": 0.04, # Lower edge required to play draws for these leagues
    "regression_factor": 0.82,
    "min_games_played": 5,
    "sharp_params": {
        "defensive_btts_drag": -0.06,
        "defensive_draw_boost": 0.06,  # Boost draws significantly for defensive matchups
        "attacking_btts_boost": 0.04,
        "btts_historical_weight": 0.15,
        "draw_prone_boost": 0.08,  # Aggressive 8% bump for historically draw-heavy teams
        "form_hot_threshold": 7,
        "form_hot_btts_boost": 0.03,
        "form_cold_threshold": 2,
        "form_cold_btts_drag": -0.04,
        "max_btts_adjustment": 0.12
    }
}

os.makedirs("configs/leagues", exist_ok=True)

for l in leagues_to_add:
    cfg = TEMPLATE.copy()
    cfg["name"] = l["name"]
    cfg["league_id"] = l["id"]
    cfg["country"] = l["country"]

    out_path = f"configs/leagues/{l['code']}.json"
    with open(out_path, "w") as f:
        json.dump(cfg, f, indent=4)

print(f"Generated {len(leagues_to_add)} high-draw config files.")

# Generate the python dict entries for SUPPORTED_LEAGUES
print("\n--- Copy-paste for SUPPORTED_LEAGUES ---")
for l in leagues_to_add:
    print(f'    "{l["code"]}": {{"id": {l["id"]}, "name": "{l["name"]}", "country": "{l["country"]}"}},')

print("\n--- Copy-paste for run_universal.py --league choices ---")
print(", ".join(f"'{l['code']}'" for l in leagues_to_add))
