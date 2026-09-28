#!/usr/bin/env python3
"""
Pre-Deployment Data Purge Script for IncPay
===========================================
Safely purges test data from the Supabase database before switching to live payments.

Order of deletion (respects foreign-key constraints):
1. transaction_logs
2. transactions
3. coupons
4. sellers

Note:
- Does NOT delete Supabase Auth users (admin credentials remain intact).
- Requires explicit user confirmation by typing 'PURGE ALL'.
"""

import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_supabase_client
from app.config import get_settings


def purge_data():
    settings = get_settings()
    print("=" * 60)
    print("      INCPAY PRE-DEPLOYMENT TEST DATA PURGE TOOL")
    print("=" * 60)
    print(f"Target Supabase Project: {settings.SUPABASE_URL}")
    print(f"Environment Setting:     {settings.ENVIRONMENT}")
    print("-" * 60)
    print("WARNING: This will permanently delete ALL data from:")
    print("  1. transaction_logs")
    print("  2. transactions")
    print("  3. coupons")
    print("  4. sellers")
    print("Admin authentication accounts in Supabase Auth will NOT be touched.")
    print("-" * 60)

    confirmation = input("Type 'PURGE ALL' to proceed with irreversible data purge: ").strip()
    if confirmation != "PURGE ALL":
        print("\n[ABORTED] Confirmation did not match 'PURGE ALL'. No data was modified.")
        sys.exit(0)

    client = get_supabase_client()
    if not client:
        print("\n[ERROR] Could not connect to Supabase. Check SUPABASE_URL and SUPABASE_KEY.")
        sys.exit(1)

    print("\nStarting purge in foreign-key dependency order...\n")

    tables_in_order = [
        ("transaction_logs", "Audit logs and webhook events"),
        ("transactions", "Customer transactions and split ledger"),
        ("coupons", "Seller payment coupons and QR codes"),
        ("sellers", "Onboarded merchant accounts"),
    ]

    total_deleted = 0
    for table_name, description in tables_in_order:
        try:
            print(f"Purging '{table_name}' ({description})...", end=" ", flush=True)
            # PostgREST requires a filter clause for bulk deletion; neq UUID zero matches all valid rows
            res = client.table(table_name).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            deleted_count = len(res.data) if res.data else 0
            total_deleted += deleted_count
            print(f"DONE ({deleted_count} rows deleted)")
        except Exception as exc:
            print(f"FAILED!\n[ERROR] Failed to purge table '{table_name}': {exc}")
            print("Purge halted due to error.")
            sys.exit(1)

    print("-" * 60)
    print(f"SUCCESS: Purge complete. {total_deleted} total records deleted.")
    print("Your Supabase database is clean and ready for live production sellers.")
    print("=" * 60)


if __name__ == "__main__":
    purge_data()
