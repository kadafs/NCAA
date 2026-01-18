import json
import os

INPUT_TEXT = "data/manual_bt_input.txt"
CONF_FILE = "data/team_conf_mapping.txt"
OUTPUT_FILE = "data/barttorvik_stats.json"

def process_manual_data():
    if not os.path.exists(INPUT_TEXT):
        print(f"Error: {INPUT_TEXT} not found.")
        return

    # Load conference mapping from text file
    conf_lookup = {}
    if os.path.exists(CONF_FILE):
        with open(CONF_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if ',' in line:
                    name, conf = line.split(',', 1)
                    conf_lookup[name.strip()] = conf.strip()
        print(f"Loaded {len(conf_lookup)} team/conference mappings.")

    processed_data = {}
    with open(INPUT_TEXT, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # The manual paste is likely tab-separated
            parts = line.split('\t')
            if len(parts) < 16:
                # Try space-separated if tabs failed
                parts = line.split('  ')
                parts = [p.strip() for p in parts if p.strip()]
            
            if len(parts) < 16: continue

            try:
                raw_name = parts[0].strip().strip('"')
                # Clean up potential BOM or brackets from manual paste
                # Keep alphanumeric and common punctuation
                name = "".join(c for c in raw_name if c.isprintable()).strip('[')
                
                # Try mapping with basic cleaning
                conf = conf_lookup.get(name, "N/A")
                
                processed_data[name] = {
                    "conf": conf,
                    "adj_off": float(parts[1]),
                    "adj_def": float(parts[2]),
                    "adj_t": float(parts[15]),
                    "efg": float(parts[7]),
                    "efg_d": float(parts[8]),
                    "ftr": float(parts[9]),
                    "ftr_d": float(parts[10]),
                    "to": float(parts[11]),
                    "to_d": float(parts[12]),
                    "or": float(parts[13]),
                    "or_d": float(parts[14])
                }
            except Exception as e:
                continue

    if processed_data:
        with open(OUTPUT_FILE, "w") as f:
            json.dump(processed_data, f, indent=2)
        print(f"Successfully processed {len(processed_data)} teams to {OUTPUT_FILE}")
        # Final spot check
        if "UC Santa Barbara" in processed_data:
            print(f"Verified UC Santa Barbara: {processed_data['UC Santa Barbara']['conf']}, eFG: {processed_data['UC Santa Barbara']['efg']}")
    else:
        print("No data was processed. Check input format.")

if __name__ == "__main__":
    process_manual_data()
