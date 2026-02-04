#!/usr/bin/env python3
"""
Supabase Audit Data Cleanup Script
Clears predictions_history and audit_summary tables to start fresh.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_KEY must be set.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def clear_audit_data():
    """Clears all records from predictions_history and audit_summary tables."""
    
    print("WARNING: This will delete ALL audit and performance history data.")
    print("This action cannot be undone.")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("Aborted. No data was deleted.")
        return
    
    try:
        # 1. Clear predictions_history
        print("\nClearing predictions_history table...")
        result = supabase.table("predictions_history").delete().neq("id", "").execute()
        print(f"[OK] Deleted {len(result.data) if result.data else 'all'} records from predictions_history")
        
        # 2. Clear audit_summary
        print("\nClearing audit_summary table...")
        result = supabase.table("audit_summary").delete().neq("league", "").execute()
        print(f"[OK] Deleted {len(result.data) if result.data else 'all'} records from audit_summary")
        
        # 3. Clear audit_metrics (rolling trend data)
        print("\nClearing audit_metrics table...")
        result = supabase.table("audit_metrics").delete().neq("id", "").execute()
        print(f"[OK] Deleted {len(result.data) if result.data else 'all'} records from audit_metrics")
        
        print("\n[OK] Audit data cleanup complete!")
        print("You can now start fresh from tomorrow's games.")
        
    except Exception as e:
        print(f"[ERROR] Error during cleanup: {e}")

if __name__ == "__main__":
    clear_audit_data()
