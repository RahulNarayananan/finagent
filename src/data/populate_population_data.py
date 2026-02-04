"""
Generate synthetic population data for 50 users with diverse spending patterns.
This provides baseline data for financial recommendations comparisons.

Run this script to populate the database with population data:
    python src/data/populate_population_data.py
"""

import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
import uuid
import numpy as np

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Please set SUPABASE_URL and SUPABASE_KEY in your .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Merchant data by category
MERCHANTS_BY_CATEGORY = {
    "Food & Dining": [
        ("Starbucks", 4.00, 12.00),
        ("McDonald's", 6.00, 15.00),
        ("Chipotle", 9.00, 18.00),
        ("Subway", 6.00, 12.00),
        ("Pizza Hut", 12.00, 35.00),
        ("Local Cafe", 3.50, 10.00),
        ("Taco Bell", 5.00, 12.00),
        ("Panda Express", 8.00, 15.00),
        ("Shake Shack", 10.00, 20.00),
        ("Panera Bread", 8.00, 16.00),
    ],
    "Groceries": [
        ("Whole Foods", 30.00, 180.00),
        ("Trader Joe's", 25.00, 120.00),
        ("Safeway", 20.00, 150.00),
        ("Costco", 50.00, 300.00),
        ("Walmart", 15.00, 100.00),
        ("Target", 20.00, 90.00),
    ],
    "Transportation": [
        ("Uber", 8.00, 45.00),
        ("Lyft", 10.00, 40.00),
        ("Shell Gas Station", 30.00, 70.00),
        ("Chevron", 25.00, 65.00),
        ("Metro Card", 30.00, 120.00),
        ("Parking Meter", 5.00, 25.00),
    ],
    "Shopping": [
        ("Amazon", 15.00, 250.00),
        ("Target", 20.00, 150.00),
        ("Nike Store", 40.00, 180.00),
        ("Zara", 30.00, 120.00),
        ("H&M", 20.00, 80.00),
        ("IKEA", 25.00, 200.00),
        ("Best Buy", 30.00, 500.00),
    ],
    "Entertainment": [
        ("Netflix", 15.99, 15.99),
        ("Spotify", 9.99, 9.99),
        ("AMC Theatres", 12.00, 30.00),
        ("Barnes & Noble", 15.00, 50.00),
        ("Steam", 10.00, 60.00),
        ("PlayStation Store", 20.00, 70.00),
    ],
    "Utilities": [
        ("AT&T", 60.00, 90.00),
        ("Verizon", 65.00, 95.00),
        ("Electric Company", 70.00, 180.00),
        ("Water Utility", 30.00, 80.00),
        ("Internet Provider", 50.00, 100.00),
    ],
    "Healthcare": [
        ("CVS Pharmacy", 10.00, 60.00),
        ("Walgreens", 12.00, 50.00),
        ("Dr. Office Copay", 25.00, 50.00),
        ("Dental Clinic", 40.00, 200.00),
    ],
    "Other": [
        ("Pet Store", 15.00, 80.00),
        ("Dry Cleaners", 10.00, 30.00),
        ("Hair Salon", 30.00, 100.00),
        ("Post Office", 5.00, 25.00),
    ]
}

# Currency distribution (most users in SGD, some in other currencies)
CURRENCIES = {
    "SGD": 0.50,  # 50%
    "USD": 0.25,  # 25%
    "EUR": 0.10,  # 10%
    "INR": 0.10,  # 10%
    "GBP": 0.05,  # 5%
}

# User spending profiles (percentage of monthly budget per category)
USER_PROFILES = {
    "balanced": {
        "Food & Dining": 0.28,
        "Groceries": 0.18,
        "Transportation": 0.15,
        "Shopping": 0.18,
        "Entertainment": 0.08,
        "Utilities": 0.08,
        "Healthcare": 0.03,
        "Other": 0.02,
    },
    "foodie": {
        "Food & Dining": 0.40,
        "Groceries": 0.15,
        "Transportation": 0.12,
        "Shopping": 0.15,
        "Entertainment": 0.08,
        "Utilities": 0.06,
        "Healthcare": 0.02,
        "Other": 0.02,
    },
    "frugal": {
        "Food & Dining": 0.15,
        "Groceries": 0.25,
        "Transportation": 0.10,
        "Shopping": 0.10,
        "Entertainment": 0.05,
        "Utilities": 0.25,
        "Healthcare": 0.08,
        "Other": 0.02,
    },
    "shopaholic": {
        "Food & Dining": 0.20,
        "Groceries": 0.12,
        "Transportation": 0.15,
        "Shopping": 0.35,
        "Entertainment": 0.10,
        "Utilities": 0.05,
        "Healthcare": 0.02,
        "Other": 0.01,
    },
    "commuter": {
        "Food & Dining": 0.22,
        "Groceries": 0.15,
        "Transportation": 0.30,
        "Shopping": 0.12,
        "Entertainment": 0.07,
        "Utilities": 0.10,
        "Healthcare": 0.03,
        "Other": 0.01,
    },
}


def generate_random_date(days_back=90):
    """Generate a random date within the last N days."""
    days_ago = random.randint(0, days_back)
    return (datetime.now() - timedelta(days=days_ago)).date()


def select_user_profile():
    """Randomly select a user spending profile."""
    profiles = list(USER_PROFILES.keys())
    weights = [0.40, 0.20, 0.15, 0.15, 0.10]  # Balanced is most common
    return random.choices(profiles, weights=weights)[0]


def select_currency():
    """Randomly select a currency based on distribution."""
    currencies = list(CURRENCIES.keys())
    weights = list(CURRENCIES.values())
    return random.choices(currencies, weights=weights)[0]


def generate_user_transactions(user_id: str, profile_name: str, monthly_budget: float, num_transactions: int, currency: str):
    """
    Generate transactions for a user based on their profile.
    
    Args:
        user_id: User's UUID
        profile_name: Spending profile type (balanced, foodie, etc.)
        monthly_budget: Total monthly budget in their currency
        num_transactions: Number of transactions to generate
        currency: User's primary currency
    """
    profile = USER_PROFILES[profile_name]
    transactions = []
    
    # Calculate budget per category (for 90 days = 3 months)
    total_budget_90days = monthly_budget * 3
    
    # Track spending per category to stay within budget
    category_budgets = {cat: total_budget_90days * pct for cat, pct in profile.items()}
    category_spent = {cat: 0.0 for cat in profile.keys()}
    
    for _ in range(num_transactions):
        # Select category based on profile (with some randomness)
        categories = list(profile.keys())
        weights = [profile[cat] for cat in categories]
        
        # Add randomness: sometimes pick a different category
        if random.random() < 0.1:
            category = random.choice(categories)
        else:
            category = random.choices(categories, weights=weights)[0]
        
        # Check if we're over budget for this category
        if category_spent[category] >= category_budgets[category]:
            # Try another category
            available_categories = [c for c in categories if category_spent[c] < category_budgets[c]]
            if not available_categories:
                continue
            category = random.choice(available_categories)
        
        # Select merchant and generate amount
        merchant, min_amt, max_amt = random.choice(MERCHANTS_BY_CATEGORY[category])
        
        # Generate amount within merchant range, but respect remaining budget
        remaining_budget = category_budgets[category] - category_spent[category]
        max_amt = min(max_amt, remaining_budget)
        
        if max_amt < min_amt:
            continue
        
        amount = round(random.uniform(min_amt, max_amt), 2)
        category_spent[category] += amount
        
        date = generate_random_date(90)
        
        # Occasionally add notes
        notes = None
        if random.random() < 0.15:  # 15% chance
            notes_options = [
                "Monthly expense",
                "Weekly shopping",
                "One-time purchase",
                "Regular subscription",
            ]
            notes = random.choice(notes_options)
        
        transaction = {
            "user_id": user_id,
            "date": date.isoformat(),
            "amount": amount,
            "merchant": merchant,
            "category": category,
            "currency": currency,
            "notes": notes,
        }
        transactions.append(transaction)
    
    return transactions


def populate_population_data(num_users=50):
    """
    Generate and insert data for multiple users to create population baseline.
    
    Args:
        num_users: Number of synthetic users to create (default: 50)
    """
    print(f"\n{'='*80}")
    print(f"GENERATING POPULATION DATA FOR {num_users} USERS")
    print(f"{'='*80}\n")
    
    all_transactions = []
    user_summary = []
    
    # Monthly budget distribution (in their local currency)
    # Most users: 1500-3000, some lower, some higher
    budget_ranges = [
        (800, 1500, 0.15),    # Low budget: 15%
        (1500, 2500, 0.50),   # Medium budget: 50%
        (2500, 4000, 0.25),   # High budget: 25%
        (4000, 6000, 0.10),   # Very high budget: 10%
    ]
    
    for i in range(num_users):
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Select profile and currency
        profile = select_user_profile()
        currency = select_currency()
        
        # Select budget
        ranges = [(r[0], r[1]) for r in budget_ranges]
        weights = [r[2] for r in budget_ranges]
        selected_range = random.choices(ranges, weights=weights)[0]
        monthly_budget = round(random.uniform(selected_range[0], selected_range[1]), 2)
        
        # Number of transactions (vary by budget level)
        if monthly_budget < 1500:
            num_trans = random.randint(25, 45)
        elif monthly_budget < 3000:
            num_trans = random.randint(40, 70)
        else:
            num_trans = random.randint(60, 100)
        
        # Generate transactions
        transactions = generate_user_transactions(user_id, profile, monthly_budget, num_trans, currency)
        all_transactions.extend(transactions)
        
        user_summary.append({
            "user_num": i + 1,
            "profile": profile,
            "currency": currency,
            "monthly_budget": monthly_budget,
            "num_transactions": len(transactions),
        })
        
        if (i + 1) % 10 == 0:
            print(f"[*] Generated data for {i + 1}/{num_users} users...")
    
    print(f"\n[*] Total transactions generated: {len(all_transactions)}")
    print(f"[*] Inserting into database...")
    
    # Insert in batches (Supabase has limits)
    batch_size = 100
    total_inserted = 0
    
    try:
        for i in range(0, len(all_transactions), batch_size):
            batch = all_transactions[i:i + batch_size]
            supabase.table("transactions").insert(batch).execute()
            total_inserted += len(batch)
            print(f"    Inserted {total_inserted}/{len(all_transactions)} transactions...")
        
        print(f"\n[SUCCESS] Database population complete!")
        
        # Print summary statistics
        print(f"\n{'='*80}")
        print("POPULATION SUMMARY")
        print(f"{'='*80}\n")
        
        profile_counts = {}
        currency_counts = {}
        total_budget = 0
        
        for user in user_summary:
            profile_counts[user['profile']] = profile_counts.get(user['profile'], 0) + 1
            currency_counts[user['currency']] = currency_counts.get(user['currency'], 0) + 1
            total_budget += user['monthly_budget']
        
        print(f"Total Users: {num_users}")
        print(f"Total Transactions: {len(all_transactions)}")
        print(f"Avg Transactions per User: {len(all_transactions) / num_users:.1f}")
        print(f"\nProfile Distribution:")
        for profile, count in sorted(profile_counts.items()):
            print(f"  - {profile.capitalize()}: {count} users ({count/num_users*100:.1f}%)")
        
        print(f"\nCurrency Distribution:")
        for curr, count in sorted(currency_counts.items()):
            print(f"  - {curr}: {count} users ({count/num_users*100:.1f}%)")
        
        print(f"\n{'='*80}")
        print("✅ Population data ready for financial recommendations feature!")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n[ERROR] Failed to insert transactions: {e}")
        print("You may need to clear existing data or check Supabase connection.")
        return


if __name__ == "__main__":
    # Generate data for 50 users
    populate_population_data(num_users=50)
