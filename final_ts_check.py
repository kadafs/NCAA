import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def check():
    url = os.getenv('NEXT_PUBLIC_SUPABASE_URL')
    key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
    if not url or not key:
        print("Missing Supabase credentials")
        return
        
    s = create_client(url, key)
    r = s.table('predictions_store').select('league, updated_at').execute()
    for x in r.data:
        print(f"{x['league']}: {x['updated_at']}")

if __name__ == "__main__":
    check()
