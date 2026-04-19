import json

leaderboard = json.load(open('data/basketball/basketball_leaderboard.json', encoding='utf-8'))['leaderboard']

# Check the script that generates the basketball_leaderboard to understand why
# For now, check if the Israel Super League teams appear at all (by fuzzy name)
search_terms = ['holon', 'raanana', 'kiryat ata', 'haemek', 'galil', 'nes ziona', 'ramat gan', 'beer sheva']
print('Searching leaderboard by fuzzy name:')
for term in search_terms:
    matches = [t['name'] for t in leaderboard if term in t['name'].lower()]
    print(f'  "{term}" -> {matches if matches else "NOT FOUND"}')
