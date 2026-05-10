import re

def check_round_8():
    with open('scratch/nbl1_dump.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    m = re.search(r'Round 8', html)
    if m:
        print(f"Found Round 8 at {m.start()}")
        # Check for fixture ID in the following 5000 chars
        f = re.search(r'data-fixture="([0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"', html[m.start():m.start()+5000])
        if f:
            fid = f.group(1)
            print(f"FID: {fid}")
            # Is it in the data?
            import os, json
            lids = [207, 208, 195, 196, 209, 210, 211, 212, 213, 214, 215, 216]
            found = False
            for lid in lids:
                path = f'data/historical/nbl1_official_{lid}.json'
                if os.path.exists(path) and fid in open(path, encoding='utf-8').read():
                    print(f"ALREADY IN DATA (League {lid})")
                    found = True
                    break
            if not found:
                print("NOT IN DATA!")
        else:
            print("No fixture ID found for Round 8")
    else:
        print("Round 8 not found")

if __name__ == "__main__":
    check_round_8()
