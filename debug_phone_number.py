#!/usr/bin/env python3
"""Debug script to check and update phone_number_id in Supabase."""

import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase = create_client(supabase_url, supabase_key)

print("=" * 80)
print("CHECKING canales_config TABLE FOR WHATSAPP ENTRIES")
print("=" * 80)

# Query all WhatsApp entries
response = supabase.table("canales_config").select(
    "id, cliente_id, canal, phone_number_id, token"
).eq("canal", "whatsapp").execute()

if response.data:
    print(f"\nFound {len(response.data)} WhatsApp entries:\n")
    for idx, row in enumerate(response.data, 1):
        print(f"{idx}. Cliente ID: {row['cliente_id']}")
        print(f"   Phone Number ID: {row['phone_number_id']}")
        print(f"   Token (first 20 chars): {row['token'][:20] if row['token'] else 'MISSING'}")
        print(f"   Row ID: {row['id']}")
        print()
else:
    print("No WhatsApp entries found!")

print("=" * 80)
print("INSTRUCTIONS TO UPDATE:")
print("=" * 80)
print("\nIf you need to update a phone_number_id:")
print("1. Find the correct row ID from above")
print("2. Update with new phone_number_id: 1108311609031850")
print("3. Run: python debug_phone_number.py <row_id> 1108311609031850")
print("\nExample: python debug_phone_number.py <row_id> 1108311609031850")

# If arguments provided, update
import sys
if len(sys.argv) == 3:
    row_id = sys.argv[1]
    new_phone_number_id = sys.argv[2]

    print(f"\nUpdating row {row_id} with new phone_number_id: {new_phone_number_id}")

    update_response = supabase.table("canales_config").update({
        "phone_number_id": new_phone_number_id
    }).eq("id", row_id).execute()

    if update_response.data:
        print(f"✓ Updated successfully!")
        print(f"  Row ID: {update_response.data[0]['id']}")
        print(f"  New Phone Number ID: {update_response.data[0]['phone_number_id']}")
    else:
        print(f"✗ Update failed!")
