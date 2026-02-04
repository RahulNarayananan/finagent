"""
Spending Analytics Module

Provides functions to analyze user spending patterns and compare them to population averages.
Used by the financial recommendations feature.
"""

from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import statistics
from supabase import Client


def calculate_user_spending_by_category(
    supabase: Client,
    user_id: str,
    time_period_days: int = 30,
    native_currency: str = "SGD"
) -> Dict[str, float]:
    """
    Calculate user's total spending by category for a given time period.
    
    Args:
        supabase: Supabase client instance
        user_id: User's UUID
        time_period_days: Number of days to look back (default: 30)
        native_currency: Currency to convert all amounts to
    
    Returns:
        Dictionary mapping category names to total amounts spent
        Example: {"Food & Dining": 450.50, "Shopping": 320.00, ...}
    """
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=time_period_days)).date()
    
    # Fetch user's transactions
    response = supabase.table("transactions")\
        .select("category, amount, currency")\
        .eq("user_id", user_id)\
        .gte("date", cutoff_date.isoformat())\
        .execute()
    
    if not response.data:
        return {}
    
    # Import here to avoid circular dependency
    from .currency_converter import convert_currency
    
    # Aggregate by category (with currency conversion)
    category_totals = {}
    
    for transaction in response.data:
        category = transaction.get("category", "Other")
        amount = float(transaction.get("amount", 0))
        currency = transaction.get("currency", "SGD")
        
        # Convert to native currency if different
        if currency != native_currency:
            converted = convert_currency(amount, currency, native_currency)
            amount = converted if converted else amount
        
        category_totals[category] = category_totals.get(category, 0) + amount
    
    return category_totals


def calculate_population_averages(
    supabase: Client,
    time_period_days: int = 30,
    native_currency: str = "SGD",
    exclude_user_id: Optional[str] = None
) -> Dict[str, float]:
    """
    Calculate average spending per category across all users (population).
    
    Args:
        supabase: Supabase client instance
        time_period_days: Number of days to look back
        native_currency: Currency to convert all amounts to
        exclude_user_id: Optionally exclude a specific user from calculation
    
    Returns:
        Dictionary mapping category names to average amounts
        Example: {"Food & Dining": 387.50, "Shopping": 275.00, ...}
    """
    # Calculate cutoff date
    cutoff_date = (datetime.now() - timedelta(days=time_period_days)).date()
    
    # Fetch all transactions in time period
    response = supabase.table("transactions")\
        .select("user_id, category, amount, currency")\
        .gte("date", cutoff_date.isoformat())\
        .execute()
    
    if not response.data:
        return {}
    
    # Import here to avoid circular dependency
    from .currency_converter import convert_currency
    
    # Group transactions by user and category
    # Structure: {user_id: {category: total_amount}}
    user_category_spending = {}
    
    for transaction in response.data:
        user_id = transaction["user_id"]
        
        # Skip excluded user if specified
        if exclude_user_id and user_id == exclude_user_id:
            continue
        
        category = transaction.get("category", "Other")
        amount = float(transaction.get("amount", 0))
        currency = transaction.get("currency", "SGD")
        
        # Convert to native currency
        if currency != native_currency:
            converted = convert_currency(amount, currency, native_currency)
            amount = converted if converted else amount
        
        if user_id not in user_category_spending:
            user_category_spending[user_id] = {}
        
        user_category_spending[user_id][category] = \
            user_category_spending[user_id].get(category, 0) + amount
    
    # Calculate average per category
    category_averages = {}
    
    # Get all unique categories
    all_categories = set()
    for user_data in user_category_spending.values():
        all_categories.update(user_data.keys())
    
    for category in all_categories:
        # Collect spending from all users who spent in this category
        category_spending = []
        
        for user_data in user_category_spending.values():
            if category in user_data:
                category_spending.append(user_data[category])
        
        # Need at least 5 users for reliable average
        if len(category_spending) < 5:
            continue
        
        # Remove outliers (beyond 3 standard deviations)
        cleaned_spending = remove_outliers(category_spending)
        
        # Calculate average of cleaned data
        if cleaned_spending:
            category_averages[category] = round(statistics.mean(cleaned_spending), 2)
    
    return category_averages


def remove_outliers(data: List[float]) -> List[float]:
    """
    Remove statistical outliers from a list of values using IQR method.
    More robust than standard deviation for financial data with extreme outliers.
    
    Args:
        data: List of numeric values
    
    Returns:
        Filtered list with outliers removed
    """
    if len(data) < 4:
        return data
    
    # Sort data to calculate quartiles
    sorted_data = sorted(data)
    n = len(sorted_data)
    
    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    q1_idx = n // 4
    q3_idx = 3 * n // 4
    q1 = sorted_data[q1_idx]
    q3 = sorted_data[q3_idx]
    
    # Calculate IQR (Interquartile Range)
    iqr = q3 - q1
    
    # Define outlier bounds (1.5 * IQR is standard)
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    
    # Filter out outliers
    return [x for x in data if lower_bound <= x <= upper_bound]


def compare_user_to_population(
    user_spending: Dict[str, float],
    population_avg: Dict[str, float]
) -> Dict[str, Tuple[float, float]]:
    """
    Compare user's spending to population averages.
    
    Args:
        user_spending: User's spending by category
        population_avg: Population averages by category
    
    Returns:
        Dictionary mapping categories to (percentage_diff, dollar_diff)
        percentage_diff: positive if overspending, negative if underspending
        dollar_diff: absolute difference in dollars
        
        Example: {
            "Shopping": (106.5, 412.50),  # 106.5% more, $412.50 over
            "Transportation": (-15.0, -45.00)  # 15% less, $45 under
        }
    """
    comparison = {}
    
    # Get all categories from both datasets
    all_categories = set(user_spending.keys()) | set(population_avg.keys())
    
    for category in all_categories:
        user_amt = user_spending.get(category, 0)
        pop_amt = population_avg.get(category, 0)
        
        # Skip if no population data for this category
        if pop_amt == 0:
            continue
        
        # Calculate differences
        dollar_diff = round(user_amt - pop_amt, 2)
        percentage_diff = round((dollar_diff / pop_amt) * 100, 1)
        
        comparison[category] = (percentage_diff, dollar_diff)
    
    return comparison


def get_top_overspending_categories(
    comparison: Dict[str, Tuple[float, float]],
    limit: int = 3
) -> List[Tuple[str, float, float]]:
    """
    Get the top N categories where user is overspending most.
    
    Args:
        comparison: Output from compare_user_to_population()
        limit: Number of top categories to return
    
    Returns:
        List of (category, percentage_diff, dollar_diff) tuples,
        sorted by percentage difference (highest first)
    """
    # Filter to only overspending (positive percentages)
    overspending = [
        (cat, pct, dollar)
        for cat, (pct, dollar) in comparison.items()
        if pct > 0
    ]
    
    # Sort by percentage difference (descending)
    overspending.sort(key=lambda x: x[1], reverse=True)
    
    return overspending[:limit]


def get_top_underspending_categories(
    comparison: Dict[str, Tuple[float, float]],
    limit: int = 3
) -> List[Tuple[str, float, float]]:
    """
    Get the top N categories where user is spending less than average.
    
    Args:
        comparison: Output from compare_user_to_population()
        limit: Number of top categories to return
    
    Returns:
        List of (category, percentage_diff, dollar_diff) tuples,
        sorted by percentage difference (lowest/most negative first)
    """
    # Filter to only underspending (negative percentages)
    underspending = [
        (cat, pct, dollar)
        for cat, (pct, dollar) in comparison.items()
        if pct < 0
    ]
    
    # Sort by percentage difference (ascending, most negative first)
    underspending.sort(key=lambda x: x[1])
    
    return underspending[:limit]
