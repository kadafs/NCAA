import json, os
import generate_advanced_metrics as gam

box1 = {
  "date": "May 04, 2026",
  "home_team": "Nunawading",
  "away_team": "Diamond Valley",
  "home_score": 90,
  "away_score": 85,
  "competition": "NBL1 South Men",
  "league_id": 209,
  "fixture_id": "1",
  "stats": {
    "home": {"pts": 90, "fgm": 30, "fga": 60, "ftm": 20, "fta": 25, "3pm": 10, "3pa": 20, "reb": 40, "orb": 10, "drb": 30, "ast": 20, "stl": 5, "blk": 3, "tov": 10, "players": [{"name": "Player A", "pts": 30, "min": "35:00", "pf": 2, "tov": 2, "stl": 1, "blk": 0, "fgm": 10, "fga": 20, "3pm": 5, "3pa": 10, "ftm": 5, "fta": 5, "orb": 2, "drb": 8, "reb": 10, "ast": 5}]},
    "away": {"pts": 85, "fgm": 28, "fga": 65, "ftm": 15, "fta": 20, "3pm": 8, "3pa": 25, "reb": 35, "orb": 8, "drb": 27, "ast": 15, "stl": 7, "blk": 2, "tov": 12, "players": [{"name": "Player X", "pts": 25, "min": "32:00", "pf": 4, "tov": 4, "stl": 3, "blk": 1, "fgm": 9, "fga": 22, "3pm": 3, "3pa": 8, "ftm": 4, "fta": 5, "orb": 3, "drb": 5, "reb": 8, "ast": 3}]}
  }
}
box2 = {
  "date": "May 02, 2026",
  "home_team": "Nunawading",
  "away_team": "Frankston",
  "home_score": 100,
  "away_score": 80,
  "competition": "NBL1 South Men",
  "league_id": 209,
  "fixture_id": "2",
  "stats": {
    "home": {"pts": 100, "fgm": 40, "fga": 80, "ftm": 10, "fta": 15, "3pm": 10, "3pa": 20, "reb": 50, "orb": 15, "drb": 35, "ast": 25, "stl": 8, "blk": 5, "tov": 8, "players": [{"name": "Player A", "pts": 40, "min": "35:00", "pf": 2, "tov": 2, "stl": 1, "blk": 0, "fgm": 15, "fga": 25, "3pm": 5, "3pa": 10, "ftm": 5, "fta": 5, "orb": 5, "drb": 5, "reb": 10, "ast": 5}]},
    "away": {"pts": 80, "fgm": 30, "fga": 70, "ftm": 10, "fta": 12, "3pm": 10, "3pa": 30, "reb": 30, "orb": 5, "drb": 25, "ast": 10, "stl": 5, "blk": 1, "tov": 15, "players": [{"name": "Player Z", "pts": 20, "min": "32:00", "pf": 4, "tov": 4, "stl": 3, "blk": 1, "fgm": 8, "fga": 20, "3pm": 4, "3pa": 10, "ftm": 0, "fta": 0, "orb": 1, "drb": 4, "reb": 5, "ast": 2}]}
  }
}
box3 = {
  "date": "May 01, 2026",
  "home_team": "Diamond Valley",
  "away_team": "Frankston",
  "home_score": 90,
  "away_score": 88,
  "competition": "NBL1 South Men",
  "league_id": 209,
  "fixture_id": "3",
  "stats": box2["stats"]
}

with open('data/historical/nbl1_official_209.json', 'w', encoding='utf-8') as f:
    json.dump([box1, box2, box3], f, indent=2)

games = [box1, box2, box3]
stats = gam.calculate_advanced_ratings(games)
print('Stats computed:', len(stats))
if len(stats) > 0:
    sdi = gam.calculate_sdi(games, '209')
    print('SDI for NBL1:', len(sdi))
    for team, index in sdi.items():
        print(f"  {team}: {index}")
