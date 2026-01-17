import json
import csv
import io
import os

CSV_CHUNKS_DIR = "data/csv_chunks"
OUTPUT_JSON = "data/barttorvik_stats.json"

def assemble_and_process():
    if not os.path.exists(CSV_CHUNKS_DIR):
        print(f"Directory {CSV_CHUNKS_DIR} not found.")
        return

    full_csv_lines = []
    chunk_files = sorted([f for f in os.listdir(CSV_CHUNKS_DIR) if f.startswith("chunk_")])
    
    for cf in chunk_files:
        with open(os.path.join(CSV_CHUNKS_DIR, cf), "r", encoding="utf-8") as f:
            full_csv_lines.extend(f.readlines())

    if not full_csv_lines:
        print("No CSV lines found in chunks.")
        return

    # Process into JSON
    # Mapping (0-indexed):
    # 0: Team, 1: AdjOE, 2: AdjDE, 7: eFG, 9: FTR, 11: TO, 13: OR, 15: Adj Tempo
    
    processed_data = {}
    
    # We also need the conference data (fallback to JSON if needed)
    conf_lookup = {}
    BARTTORVIK_JSON_FILE = "data/barttorvik_team_results.json" # Downloaded via browser if needed
    if os.path.exists(BARTTORVIK_JSON_FILE):
        with open(BARTTORVIK_JSON_FILE, "r") as f:
            raw_json = json.load(f)
            for team_data in raw_json:
                name = team_data[1]
                conf = team_data[2]
                conf_lookup[name] = conf

    for line in full_csv_lines:
        if not line.strip(): continue
        # Use csv reader to handle quotes properly
        reader = csv.reader(io.StringIO(line))
        try:
            row = next(reader)
            if len(row) < 16: continue
            name = row[0]
            processed_data[name] = {
                "conf": conf_lookup.get(name, "N/A"),
                "adj_off": float(row[1]),
                "adj_def": float(row[2]),
                "adj_t": float(row[15]),
                "efg": float(row[7]),
                "efg_d": float(row[8]),
                "ftr": float(row[9]),
                "ftr_d": float(row[10]),
                "to": float(row[11]),
                "to_d": float(row[12]),
                "or": float(row[13]),
                "or_d": float(row[14])
            }
        except Exception as e:
            continue

    if processed_data:
        os.makedirs("data", exist_ok=True)
        with open(OUTPUT_JSON, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Assembled and saved {len(processed_data)} teams to {OUTPUT_JSON}")

if __name__ == "__main__":
    assemble_and_process()
