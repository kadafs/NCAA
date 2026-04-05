all_names = ["Gravelines", "Gravelines-Dunkerque", "Le Portel", "ESSM Le Portel", "Chalon", "Chalon/Saone", "Monaco", "AS Monaco", "Dijon", "JDA Dijon", "ZKK Kraljevo W"]

team_name_map = {}
sorted_names = sorted(all_names, key=len, reverse=True)
for name in sorted_names:
    matched = False
    name_lower = name.lower()
    for primary in set(team_name_map.values()):
        pri_lower = primary.lower()
        if name_lower in pri_lower or pri_lower in name_lower:
            team_name_map[name] = primary
            matched = True
            break
        # word overlap for tokens >= 4 chars
        nw = set(w for w in name_lower.replace("-"," ").replace("/"," ").split() if len(w) >= 4)
        pw = set(w for w in pri_lower.replace("-"," ").replace("/"," ").split() if len(w) >= 4)
        if nw & pw:
            team_name_map[name] = primary
            matched = True
            break
    if not matched:
        team_name_map[name] = name

import json
print(json.dumps(team_name_map, indent=2))
