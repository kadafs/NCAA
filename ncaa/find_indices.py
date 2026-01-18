import requests

def find_indices():
    url = 'https://barttorvik.com/2026_team_results.json'
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    data = r.json()

    # Known Stats (from Michigan page and research)
    # Michigan: eFG 59.4, eFG D 42.0, TO 15.9, TO D 17.3, OR 34.5, OR D 27.8, FTR 39.4, FTR D 27.5
    # Kansas:   eFG 55.8, eFG D 49.3, TO 11.7, TO D 18.0, OR 29.8, OR D 25.1, FTR 31.8, FTR D 21.7
    
    m = next(t for t in data if t[1] == 'Michigan')
    k = next(t for t in data if t[1] == 'Kansas')
    
    stats_m = {
        'efg': 59.4, 'efgd': 42.0, 
        'to': 15.9, 'tod': 17.3, 
        'or': 34.5, 'ord': 27.8, 
        'ftr': 39.4, 'ftrd': 27.5
    }
    stats_k = {
        'efg': 55.8, 'efgd': 49.3, 
        'to': 11.7, 'tod': 18.0, 
        'or': 29.8, 'ord': 25.1, 
        'ftr': 31.8, 'ftrd': 21.7
    }

    # Also check if they are in 0-1 range (percentages)
    stats_m_p = {k: v/100.0 for k, v in stats_m.items()}
    stats_k_p = {k: v/100.0 for k, v in stats_k.items()}

    results = []
    for key in stats_m:
        print(f"\nSearching for {key}:")
        target_m = stats_m[key]
        target_k = stats_k[key]
        target_m_p = stats_m_p[key]
        target_k_p = stats_k_p[key]
        
        for i in range(len(m)):
            v1, v2 = m[i], k[i]
            if isinstance(v1, (int, float)) and isinstance(v2, (int, float)):
                # Check raw value
                if abs(v1 - target_m) < 0.5 and abs(v2 - target_k) < 0.5:
                    print(f"  [RAW] Match at Index {i}: {v1}, {v2}")
                # Check percentage value
                if abs(v1 - target_m_p) < 0.005 and abs(v2 - target_k_p) < 0.005:
                    print(f"  [PCT] Match at Index {i}: {v1}, {v2}")

if __name__ == "__main__":
    find_indices()
