import re

def check_dates():
    with open('scratch/nbl1_dump.html', 'r', encoding='utf-8') as f:
        html = f.read()

    starts = re.findall(r'startTimeLocal":"([^"]+)"', html)
    if starts:
        unique_starts = sorted(list(set(starts)))
        print(f"Found {len(unique_starts)} unique start times")
        print("Latest 10:")
        for s in unique_starts[-10:]:
            print(f"  {s}")
    else:
        print("No startTimeLocal found")

if __name__ == "__main__":
    check_dates()
