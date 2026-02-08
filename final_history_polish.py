import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def final_polish():
    corrections = [
        {"matchup": "Nebraska @ Rutgers", "total": 144.5},
        {"matchup": "Mississippi @ Texas", "total": 144.5}
    ]
    
    for c in corrections:
        print(f"Repairing {c['matchup']} manually...")
        res = supabase.table("predictions_history").select("*").eq("game_date", "2026-02-07").ilike("matchup", f"%{c['matchup']}%").execute()
        for r in res.data:
            model_total = r['model_total']
            new_edge = round(model_total - c['total'], 2)
            supabase.table("predictions_history").update({
                "market_total": c['total'],
                "edge": new_edge,
                "status": "pending",
                "updated_at": datetime.now().isoformat()
            }).eq("id", r['id']).execute()
            print(f"  Updated ID {r['id']}")

if __name__ == "__main__":
    final_polish()
