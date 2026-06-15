import os
import json
import statsapi

def build_player_map():
    print("Building static player map for all active MLB rosters...")
    # Get all active MLB teams
    teams = statsapi.get('teams', {'sportId': 1, 'activeStatus': 'Y'}).get('teams', [])
    
    player_map = {}
    
    for t in teams:
        team_id = t['id']
        team_name = t['name']
        print(f"Fetching roster for {team_name}...")
        
        try:
            roster = statsapi.get('team_roster', {'teamId': team_id}).get('roster', [])
            
            # Batch up to 50 players at a time
            player_ids = []
            for p in roster:
                pid = p.get('person', {}).get('id')
                if pid:
                    player_ids.append(str(pid))
            
            # Chunking list of IDs
            chunk_size = 50
            for i in range(0, len(player_ids), chunk_size):
                chunk = player_ids[i:i + chunk_size]
                id_str = ",".join(chunk)
                
                try:
                    info = statsapi.get('people', {'personIds': id_str}).get('people', [])
                    for p_info in info:
                        pid = p_info.get('id')
                        name = p_info.get('fullName')
                        bat_side = p_info.get('batSide', {}).get('code', 'R')
                        pitch_hand = p_info.get('pitchHand', {}).get('code', 'R')
                        
                        if name:
                            player_map[name] = {
                                "id": pid,
                                "bat_side": bat_side,
                                "pitch_hand": pitch_hand
                            }
                except Exception as e:
                    print(f"  Error looking up batch: {e}")
                    
        except Exception as e:
            print(f"Error fetching roster for {team_name}: {e}")
            
    # Save the map
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    os.makedirs(data_dir, exist_ok=True)
    out_path = os.path.join(data_dir, 'player_map.json')
    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(player_map, f, indent=4)
        
    print(f"\nDone! Successfully cached {len(player_map)} active players to {out_path}.")

if __name__ == "__main__":
    build_player_map()
