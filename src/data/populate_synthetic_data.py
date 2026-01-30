"""
Script to populate the Supabase database with synthetic financial data.
Run this script to test the FinAgent application with realistic sample data.
"""

import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Sample data for realistic transactions
MERCHANTS = [
    # Food & Dining
    ("Starbucks", "Food & Dining", 5.50, 15.00),
    ("McDonald's", "Food & Dining", 8.00, 20.00),
    ("Whole Foods", "Groceries", 20.00, 150.00),
    ("Trader Joe's", "Groceries", 15.00, 80.00),
    ("Chipotle", "Food & Dining", 10.00, 18.00),
    ("Subway", "Food & Dining", 7.00, 12.00),
    ("Pizza Hut", "Food & Dining", 15.00, 35.00),
    ("Local Cafe", "Food & Dining", 4.00, 12.00),
    
    # Transportation
    ("Uber", "Transportation", 8.00, 35.00),
    ("Lyft", "Transportation", 10.00, 40.00),
    ("Shell Gas Station", "Transportation", 30.00, 60.00),
    ("Metro Card", "Transportation", 20.00, 100.00),
    
    # Shopping
    ("Amazon", "Shopping", 15.00, 200.00),
    ("Target", "Shopping", 25.00, 150.00),
    ("Best Buy", "Electronics", 50.00, 800.00),
    ("Nike Store", "Shopping", 40.00, 200.00),
    ("Zara", "Shopping", 30.00, 120.00),
    
    # Utilities & Services
    ("Netflix", "Entertainment", 15.99, 15.99),
    ("Spotify", "Entertainment", 9.99, 9.99),
    ("LA Fitness", "Health & Fitness", 45.00, 45.00),
    ("AT&T", "Utilities", 75.00, 75.00),
    ("Electric Company", "Utilities", 80.00, 150.00),
    
    # Healthcare
    ("CVS Pharmacy", "Healthcare", 10.00, 50.00),
    ("Walgreens", "Healthcare", 12.00, 45.00),
    ("Dr. Smith's Office", "Healthcare", 50.00, 200.00),
    
    # Entertainment
    ("AMC Theatres", "Entertainment", 12.00, 30.00),
    ("Barnes & Noble", "Entertainment", 15.00, 50.00),
    ("Steam", "Entertainment", 10.00, 60.00),
]

FRIEND_NAMES = [
    ("Alice Johnson", "+1-555-0101"),
    ("Bob Chen", "+1-555-0102"),
    ("Charlie Davis", "+1-555-0103"),
    ("Diana Garcia", "+1-555-0104"),
    ("Ethan Williams", "+1-555-0105"),
    ("Fiona Martinez", "+1-555-0106"),
]

DEBT_DESCRIPTIONS = [
    "Dinner at Italian restaurant",
    "Group movie tickets",
    "Shared Uber ride home",
    "Grocery shopping for party",
    "Concert tickets",
    "Weekend trip expenses",
    "Lunch bill split",
    "Coffee run",
]


def generate_random_date(days_back=90):
    """Generate a random date within the last N days."""
    days_ago = random.randint(0, days_back)
    return (datetime.now() - timedelta(days=days_ago)).date()


def generate_transactions(user_id: str, count: int = 50):
    """Generate synthetic transaction data."""
    transactions = []
    
    for _ in range(count):
        merchant, category, min_amount, max_amount = random.choice(MERCHANTS)
        amount = round(random.uniform(min_amount, max_amount), 2)
        date = generate_random_date()
        
        # Randomly add notes to some transactions
        notes = None
        if random.random() < 0.3:  # 30% chance of having notes
            notes_options = [
                "Work expense - need reimbursement",
                "Birthday gift",
                "Monthly subscription",
                "Emergency purchase",
                "Regular weekly shopping",
                "Special occasion",
            ]
            notes = random.choice(notes_options)
        
        transaction = {
            "user_id": user_id,
            "date": date.isoformat(),
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "notes": notes,
        }
        transactions.append(transaction)
    
    return transactions


def generate_friends(user_id: str):
    """Generate synthetic friends data."""
    friends = []
    
    for name, phone in FRIEND_NAMES:
        friend = {
            "user_id": user_id,
            "name": name,
            "phone": phone,
        }
        friends.append(friend)
    
    return friends


def generate_debts(user_id: str, friend_ids: list, count: int = 15):
    """Generate synthetic debts data."""
    debts = []
    
    for _ in range(count):
        friend_id = random.choice(friend_ids)
        amount = round(random.uniform(10.00, 150.00), 2)
        description = random.choice(DEBT_DESCRIPTIONS)
        is_paid = random.choice([True, False])
        
        debt = {
            "user_id": user_id,
            "friend_id": friend_id,
            "amount": amount,
            "description": description,
            "is_paid": is_paid,
        }
        debts.append(debt)
    
    return debts


def populate_database(user_id: str = None):
    """
    Main function to populate the database with synthetic data.
    
    Args:
        user_id: The UUID of the user to populate data for. 
                 If None, you'll need to use the authenticated user's ID.
    """
    
    if not user_id:
        print("[!] No user_id provided. Using a sample UUID for demonstration.")
        print("[!] In production, you should use the authenticated user's ID from Supabase Auth.")
        user_id = str(uuid.uuid4())
        print(f"[*] Using user_id: {user_id}")
    
    print("\n[*] Starting database population...")
    
    # Generate and insert transactions
    print("\n[*] Generating transactions...")
    transactions = generate_transactions(user_id, count=50)
    
    try:
        response = supabase.table("transactions").insert(transactions).execute()
        print(f"[+] Successfully inserted {len(transactions)} transactions")
    except Exception as e:
        print(f"[-] Error inserting transactions: {e}")
        return
    
    # Generate and insert friends
    print("\n[*] Generating friends...")
    friends = generate_friends(user_id)
    
    try:
        response = supabase.table("friends").insert(friends).execute()
        friend_ids = [friend["id"] for friend in response.data]
        print(f"[+] Successfully inserted {len(friends)} friends")
    except Exception as e:
        print(f"[-] Error inserting friends: {e}")
        return
    
    # Generate and insert debts
    print("\n[*] Generating debts...")
    debts = generate_debts(user_id, friend_ids, count=15)
    
    try:
        response = supabase.table("debts").insert(debts).execute()
        print(f"[+] Successfully inserted {len(debts)} debts")
    except Exception as e:
        print(f"[-] Error inserting debts: {e}")
        return
    
    print("\n[SUCCESS] Database population complete!")
    print(f"\nSummary:")
    print(f"   - Transactions: {len(transactions)}")
    print(f"   - Friends: {len(friends)}")
    print(f"   - Debts: {len(debts)}")
    print(f"\nTip: You can now test the FinAgent app with this synthetic data!")


if __name__ == "__main__":
    # You can pass a specific user_id here, or get it from Supabase Auth
    # For testing purposes, we'll generate a random one
    populate_database()
