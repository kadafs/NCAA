import json

updates = {
    "227": ("croatia-liga", "https://www.proballers.com/basketball/league/185/croatia-liga/schedule"),
    "44": ("greece-heba-a2", "https://www.proballers.com/basketball/league/275/greece-heba-a2/schedule"),
    "85": ("serbia-kls", "https://www.proballers.com/basketball/league/285/serbia-kls/schedule"),
    "93": ("sweden-basketligan", "https://www.proballers.com/basketball/league/190/sweden-basketligan/schedule")
}

for lid, (name, url) in updates.items():
    path = f"configs/leagues/{lid}.json"
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        
        d["proballers_name"] = name
        d["proballers_url"] = url
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=4)
        print(f"Successfully updated league ID {lid} ({name})")
    except Exception as e:
        print(f"Failed to update {lid}: {e}")
