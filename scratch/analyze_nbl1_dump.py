import re

def analyze_dump():
    with open('scratch/nbl1_dump.html', 'r', encoding='utf-8') as f:
        html = f.read().lower()

    # Find fixtureId patterns
    # The dump showed: data-fixture="243dcba9-da64-11f0-b44d-314247ea452a"
    fixture_ids = re.findall(r'data-fixture="([0-9a-f]{8}-[0-9a-f]{4}-1[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12})"', html)
    unique_fids = set(fixture_ids)
    print(f"Found {len(unique_fids)} unique V1 fixture IDs in data-fixture attributes")

    # Check for other UUIDs
    all_uuids = re.findall(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', html)
    print(f"Total UUIDs in file: {len(all_uuids)}")
    print(f"Unique UUIDs in file: {len(set(all_uuids))}")
    
    v1_uuids = [u for u in set(all_uuids) if u.split('-')[2].startswith('1')]
    print(f"Unique V1 UUIDs in file: {len(v1_uuids)}")

    # Sample some FIDs
    print("\nSample FIDs:")
    for fid in sorted(list(unique_fids))[:10]:
        print(f"  {fid}")

if __name__ == "__main__":
    analyze_dump()
