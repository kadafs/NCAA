import json
from collections import defaultdict

with open("data/league_slug_map.json", "r") as f:
    mapping = json.load(f)

# Reverse map: api_id -> list of slugs
reverse_map = defaultdict(list)
for slug, api_id in mapping.items():
    reverse_map[api_id].append(slug)

duplicates = {k: v for k, v in reverse_map.items() if len(v) > 1}

print(f"Total mappings: {len(mapping)}")
print(f"Total unique IDs: {len(reverse_map)}")
print(f"IDs with multiple slugs: {len(duplicates)}")

print("\n--- DUPLICATES ---")
for api_id, slugs in sorted(duplicates.items()):
    print(f"ID {api_id}:")
    for s in slugs:
        print(f"  - {s}")

# Let's delete the exact ones we know are wrong based on analysis
to_delete = [
    "bulgaria-division-a", # 115 (Should be Cyprus Division A)
    "italy-serie-b-girone-a", # 242 (Overwrites Serie A2)
    "italy-serie-b-girone-b", # 53 (Overwrites Serie A1 W)
    "france-nm1", # 2 (Overwrites LNB)
    "france-u21-elite", # 2 (Overwrites LNB)
    "france-u21-elite-2", # 232 (Overwrites Ligue 2 W)
    "france-lf2-w", # 10 (Overwrites LFB W)
    "finland-1st-division-b", # 229 (Overwrites Div A)
    "spain-leb-gold", # 117 (Overwrites ACB)
    "switzerland-nlb", # 100 (Overwrites SBL)
    "portugal-liga-profissional", # 261 (Overwrites Proliga)
    "basketball-africa-league", # 374 (Overwrites Belgium Pro)
    "bosnia-division-i", # 409 (Overwrites Lebanon Div 1)
    "world-cup", # 156 (Overwrites Poland PBA Cup)
    "world-cup-w", # 70 (Overwrites Poland Cup W)
    "adriatic-junior-aba-league", # 198 (Overwrites ABA League)
    "u20-european-championship-div-b",
    "u20-european-championship-w-div-b",
    "u16-european-championship-div-b",
    "u16-european-championship-w-div-b",
    "u16-european-championship",
    "u16-european-championship-w",
    "u18-european-championship",
    "u18-european-championship-w",
    "u20-european-championship",
    "u20-european-championship-w"
]

cleaned_mapping = {s: id for s, id in mapping.items() if s not in to_delete}

with open("data/league_slug_map_cleaned.json", "w") as f:
    json.dump(cleaned_mapping, f, indent=2)

print("\nSaved cleaned mapping to data/league_slug_map_cleaned.json")
