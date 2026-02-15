import pandas as pd
import json
import os
import sys
import io
import re

# Output file path (RAW format for fetch script)
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'barttorvik_raw_conf.json')

def clean_team_name(name):
    name = str(name)
    # Remove (H) Opponent or (A) Opponent or (#) Rank
    # Example: "Duke (H) 25 Clemson" -> "Duke "
    name = re.sub(r'\s*\(.*', '', name)
    
    # Remove "vs." Opponent
    # Example: "Virginia vs. 40 Ohio St." -> "Virginia"
    if ' vs.' in name:
        name = name.split(' vs.')[0]
    
    return name.strip()

def main():
    print("=" * 60)
    print(" BARTTORVIK BOARD IMPORTER (CSV / Clipboard v8 - Strict Integrity)")
    print("=" * 60)
    
    df = None
    
    # Method 0: Check for 'data/barttorvik.csv' (User Request)
    csv_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'barttorvik.csv')
    if os.path.exists(csv_file):
        print(f"Found CSV file: {csv_file}")
        try:
            print("Reading from CSV...")
            # Try comma first
            df = pd.read_csv(csv_file)
            if len(df.columns) <= 1:
                print("  -> CSV has weird separator? Trying tab...")
                df = pd.read_csv(csv_file, sep='\t')
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            df = None

    # Method 1: Try reading clipboard with tab
    if df is None:
        try:
            print("Attempt 1: Reading clipboard (Tab separated)...")
            df = pd.read_clipboard(sep='\t')
            if df is not None and len(df.columns) <= 1:
                df = None
        except Exception as e:
            pass 
        
    # Method 2: Try comma separated (CSV text on clipboard)
    if df is None:
        try:
            print("Attempt 2: Reading clipboard (Comma separated)...")
            df = pd.read_clipboard(sep=',')
            if df is not None and len(df.columns) <= 1:
                df = None
        except Exception as e:
            pass

    # Method 3: Try whitespace
    if df is None:
        try:
            print("Attempt 3: Reading clipboard (Whitespace separated)...")
            df = pd.read_clipboard(sep=r'\s+')
        except Exception as e:
            pass

    # Method 4: File Fallback (manual_paste.txt)
    if df is None:
        print("\nCould not read clipboard directly. Let's try the fallback file.")
        fallback_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'manual_paste.txt')
        if os.path.exists(fallback_path):
            print(f"Reading from {fallback_path}...")
            try:
                # Try header=0 (default)
                df = pd.read_csv(fallback_path, sep='\t')
                if len(df.columns) <= 1: df = pd.read_csv(fallback_path, sep=',')
                if len(df.columns) <= 1: df = pd.read_csv(fallback_path, sep=r'\s+')
            except Exception as e:
                print(f"ERROR reading file: {e}")
        else:
            print(f"\n❌ ACTION REQUIRED:")
            print(f"OPTION A: Save your data as 'data/barttorvik.csv'")
            print(f"OPTION B: Paste data into 'data/manual_paste.txt'")
            print(f"Then run this script again.")
            sys.exit(1)

    if df is None:
        print("No valid data found.")
        sys.exit(1)

    # Normalize columns
    df.columns = [str(c).strip() for c in df.columns]
    
    # Check for required columns 
    def get_col(candidates):
        for c in df.columns:
            for cand in candidates:
                if cand.lower() == str(c).lower() or cand.lower() in str(c).lower():
                    return c
        return None

    # Mapping (Strict Requirements)
    # We NEED both Offense (e.g. eFG) and Defense (e.g. eFG_D / EFGD%)
    col_map = {
        'Team': get_col(['Team', 'School']),
        'AdjOE': get_col(['AdjOE', 'Adj O', 'OE']),
        'AdjDE': get_col(['AdjDE', 'Adj D', 'DE']),
        'AdjT': get_col(['Adj T', 'Tempo', 'AdjT']),
        'eFG': get_col(['eFG', 'EFG%', 'eFG%']),
        'eFG_D': get_col(['eFG%D', 'EFGD%', 'Def eFG', 'O eFG', 'DEfg']), 
        'TO': get_col(['TO%', 'TOR']),
        'TO_D': get_col(['TO%D', 'TORD', 'Def TO', 'D TO']),
        'OR': get_col(['OR%', 'ORB']),
        'OR_D': get_col(['OR%D', 'DRB', 'D OR']), 
        'FTR': get_col(['FTR', 'FTA', 'FT Rate']),
        'FTR_D': get_col(['FTRD', 'Def FTR', 'D FTR']),
        'Games': get_col(['G', 'Gm', 'Games']) # Optional-ish, but good to have
    }
    
    # STRICT CHECK
    required = ['Team', 'AdjOE', 'AdjDE', 'AdjT', 'eFG', 'eFG_D', 'TO', 'TO_D', 'OR', 'OR_D', 'FTR', 'FTR_D']
    missing_cols = [k for k in required if not col_map[k]]
    
    if missing_cols:
        print(f"\n❌ CRITICAL ERROR: Missing required columns: {missing_cols}")
        print(f"We found some headers in your file: {list(df.columns)[:5]}...")
        print("Please check your CSV mappings or re-export.")
        sys.exit(1)

    # Build Output
    raw_data = []
    
    print("\nProcessing teams (with strict integrity)...")
    
    t_idx = df.columns.get_loc(col_map['AdjT'])
    
    for idx, row in df.iterrows():
        try:
            raw_name = row[col_map['Team']]
            if "Team" in str(raw_name): continue 
            
            team = clean_team_name(raw_name)
            
            def val(c):
                # Now guaranteed that c exists (because of strict check above)
                try:
                    s = str(row[c]).replace('%','')
                    return float(s)
                except:
                    return 0.0

            # --- SMART TEMPO FIX ---
            adj_t = 0.0
            if True: # Always run logic if t_idx known
                # Get raw value by positional index in case names are weird
                try:
                    raw_t = row.iloc[t_idx]
                    val_t = 0.0
                    try: val_t = float(str(raw_t).replace('%',''))
                    except: val_t = 0.0
                    
                    # Heuristic: Tempo should be > 50. If < 40 or negative, check left neighbor
                    if val_t < 40:
                        # Check Left
                        if t_idx > 0:
                            try:
                                left_val = float(str(row.iloc[t_idx - 1]).replace('%',''))
                                if left_val > 50:
                                    val_t = left_val
                            except: pass
                    
                    adj_t = val_t
                except:
                    adj_t = val(col_map['AdjT'])

            item = [""] * 16
            item[0] = team
            item[1] = val(col_map['AdjOE']) 
            item[2] = val(col_map['AdjDE'])
            
            item[7] = val(col_map['eFG'])
            item[8] = val(col_map['eFG_D'])
            item[9] = val(col_map['FTR'])
            item[10] = val(col_map['FTR_D'])
            item[11] = val(col_map['TO'])
            item[12] = val(col_map['TO_D'])
            item[13] = val(col_map['OR'])
            item[14] = val(col_map['OR_D'])
            item[15] = adj_t # Use smart corrected value
            
            raw_data.append(item)
        except Exception as e:
            # Skip rows causing internal errors
            continue

    print(f"Parsed {len(raw_data)} teams.")
    
    if len(raw_data) > 0:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(raw_data, f, indent=2)
        print(f"✓ Saved cleaned data to {OUTPUT_FILE}")
        
        # Run fetch
        print("Running fetch script...")
        os.system(f"python {os.path.join(os.path.dirname(__file__), 'fetch_barttorvik_conf.py')}")
        
    else:
        print("No valid data parsed.")

if __name__ == "__main__":
    main()
