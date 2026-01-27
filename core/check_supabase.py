import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check_tables():
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    
    if not url or not key:
        print("Missing URL or Key")
        return

    supabase = create_client(url, key)
    
    tables_to_check = ['predictions_history', 'audit_metrics', 'predictions_store']
    
    for table in tables_to_check:
        try:
            res = supabase.table(table).select("*").limit(1).execute()
            print(f"Table {table}: EXISTS")
        except Exception as e:
            print(f"Table {table}: MISSING or ERROR ({e})")

if __name__ == "__main__":
    check_tables()
