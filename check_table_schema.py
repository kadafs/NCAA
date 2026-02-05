import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_schema():
    # Fetch one row to verify columns
    res = supabase.table("predictions_history").select("*").limit(1).execute()
    if res.data:
        keys = res.data[0].keys()
        print(f"Columns: {list(keys)}")
        if "mode" in keys:
            print("Found 'mode' column.")
        else:
            print("'mode' column NOT found.")
    else:
        print("Table is empty, cannot verify columns.")

if __name__ == "__main__":
    check_schema()
