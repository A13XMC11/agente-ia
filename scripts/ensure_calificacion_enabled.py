#!/usr/bin/env python3
"""
Script to verify and enable lead scoring (calificacion) module for all clients.
Run this to ensure all clients have calificacion enabled.
"""

import json
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def ensure_calificacion_enabled():
    """Ensure calificacion module is enabled for all clients."""
    print("\n=== LEAD SCORING MODULE VERIFICATION ===\n")

    try:
        # Fetch all clients
        response = supabase.table("agentes").select("*").execute()
        clients = response.data

        if not clients:
            print("❌ No clients found in agentes table")
            return

        print(f"Found {len(clients)} client(s) in database\n")

        for client in clients:
            client_id = client.get("cliente_id", "unknown")
            active_modules = client.get("active_modules", {})

            print(f"Client: {client_id}")
            print(f"  Current modules: {json.dumps(active_modules, ensure_ascii=False, indent=4)}")

            # Check if calificacion is present
            if "calificacion" not in active_modules:
                print(f"  ⚠️  MISSING: calificacion not in active_modules")
                active_modules["calificacion"] = True
                update_needed = True
            elif active_modules["calificacion"] is False:
                print(f"  ❌ DISABLED: calificacion is False")
                active_modules["calificacion"] = True
                update_needed = True
            else:
                print(f"  ✅ OK: calificacion is enabled")
                update_needed = False

            if update_needed:
                # Update the client configuration
                update_response = (
                    supabase.table("agentes")
                    .update({
                        "active_modules": active_modules,
                        "updated_at": datetime.utcnow().isoformat(),
                    })
                    .eq("cliente_id", client_id)
                    .execute()
                )
                if update_response.data:
                    print(f"  ✅ UPDATED: calificacion now enabled\n")
                else:
                    print(f"  ❌ UPDATE FAILED\n")
            else:
                print()

        print("=== VERIFICATION COMPLETE ===\n")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    ensure_calificacion_enabled()
