import os
import json
from supabase import create_client, Client
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: Missing Supabase credentials in .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def inspect():
    tables = ["predictions_history", "audit_summary", "audit_metrics", "predictions_store"]
    
    for table in tables:
        print(f"\n--- Table: {table} ---")
        try:
            # Get count
            count_res = supabase.table(table).select("*", count="exact").limit(1).execute()
            count = count_res.count if hasattr(count_res, 'count') else "Unknown"
            print(f"Total Rows: {count}")
            
            # Get samples
            samples = supabase.table(table).select("*").order("updated_at", descending=True).limit(3).execute()
            if samples.data:
                for i, row in enumerate(samples.data):
                    # Truncate some fields for readability
                    display_row = {k: (str(v)[:50] + "..." if isinstance(v, str) and len(v) > 50 else v) for k, v in row.items()}
                    print(f" Sample {i+1}: {display_row}")
            else:
                print(" No data found.")
        except Exception as e:
            print(f" Error inspecting {table}: {e}")

    # Check per-category graded counts
    print("\n--- Graded Counts per Category in predictions_history ---")
    categories = [
        {'league': 'nba', 'mode': 'safe'},
        {'league': 'nba', 'mode': 'full'},
        {'league': 'ncaa', 'mode': 'safe'},
        {'league': 'ncaa', 'mode': 'full'}
    ]
    for cat in categories:
        try:
            res = supabase.table("predictions_history") \
                .select("*", count="exact") \
                .ilike("league", cat['league']) \
                .eq("mode", cat['mode']) \
                .eq("status", "graded") \
                .execute()
            print(f" {cat['league'].upper()} ({cat['mode']}): {res.count}")
        except Exception as e:
            print(f" Error checking {cat['league']} {cat['mode']}: {e}")

if __name__ == "__main__":
    inspect()
