
import os
import sys
from dotenv import load_dotenv
from supabase import create_client, Client
import time

# Add src to python path to import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.core.embeddings import generate_embedding

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def backfill_embeddings():
    print("[*] Starting embedding backfill...")
    
    # 1. Fetch transactions with null embeddings
    # Note: 'is' operator for null check in PostgREST is 'is.null', but with python client .is_("embedding", "null")
    try:
        response = supabase.table("transactions").select("*").filter("embedding", "is", "null").execute()
        transactions = response.data
    except Exception as e:
        print(f"[-] Error fetching transactions: {e}")
        return

    if not transactions:
        print("[*] No transactions need embeddings.")
        return

    print(f"[*] Found {len(transactions)} transactions to process.")
    
    count = 0
    errors = 0
    
    for tx in transactions:
        try:
            # Construct text representation for embedding
            # "Merchant: Starbucks. Category: Food. Notes: Coffee with friend."
            text_parts = [f"Merchant: {tx['merchant']}"]
            if tx['category']:
                 text_parts.append(f"Category: {tx['category']}")
            if tx['notes']:
                text_parts.append(f"Notes: {tx['notes']}")
            
            text_to_embed = ". ".join(text_parts)
            
            # Generate embedding
            embedding = generate_embedding(text_to_embed)
            
            # Update record
            supabase.table("transactions").update({"embedding": embedding}).eq("id", tx['id']).execute()
            
            count += 1
            if count % 5 == 0:
                print(f"[*] Processed {count}/{len(transactions)}...")
                
        except Exception as e:
            print(f"[-] Error processing transaction {tx['id']}: {e}")
            errors += 1
            
    print(f"\n[SUCCESS] Backfill complete.")
    print(f"Processed: {count}")
    print(f"Errors: {errors}")

if __name__ == "__main__":
    backfill_embeddings()
