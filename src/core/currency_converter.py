"""
Currency conversion utilities using free exchange rate API.
Uses exchangerate.host - completely free, no API key needed.
"""

import requests
from typing import Dict, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path

# Cache file for exchange rates
CACHE_FILE = Path(__file__).parent.parent.parent / ".cache" / "exchange_rates.json"
CACHE_DURATION = timedelta(hours=24)

# Common currency symbols
CURRENCY_SYMBOLS = {
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
    "SGD": "S$",
    "INR": "₹",
    "JPY": "¥",
    "AUD": "A$",
    "CNY": "¥",
    "MYR": "RM",
    "THB": "฿",
    "KRW": "₩",
    "CAD": "C$",
}

def get_currency_symbol(currency_code: str) -> str:
    """Get the symbol for a currency code."""
    return CURRENCY_SYMBOLS.get(currency_code.upper(), currency_code)

def _load_cached_rates() -> Optional[Dict]:
    """Load exchange rates from cache if valid."""
    try:
        if CACHE_FILE.exists():
            with open(CACHE_FILE, 'r') as f:
                cache_data = json.load(f)
                cache_time = datetime.fromisoformat(cache_data['timestamp'])
                
                # Check if cache is still valid
                if datetime.now() - cache_time < CACHE_DURATION:
                    return cache_data['rates']
    except Exception as e:
        print(f"[Currency] Cache load error: {e}")
    return None

def _save_cached_rates(rates: Dict):
    """Save exchange rates to cache."""
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        cache_data = {
            'timestamp': datetime.now().isoformat(),
            'rates': rates
        }
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache_data, f)
    except Exception as e:
        print(f"[Currency] Cache save error: {e}")

def get_exchange_rates(base_currency: str = "USD") -> Optional[Dict[str, float]]:
    """
    Fetch exchange rates from frankfurter.app API (European Central Bank data).
    Returns a dict of {currency_code: rate} relative to base_currency.
    Completely free, no API key required.
    """
    # Try cache first
    cached_rates = _load_cached_rates()
    if cached_rates and cached_rates.get('base') == base_currency:
        print(f"[Currency] Using cached rates for {base_currency}")
        return cached_rates
    
    try:
        # Use frankfurter.app - free European Central Bank data, no API key
        url = f"https://api.frankfurter.app/latest?from={base_currency}"
        print(f"[Currency] Fetching rates from: {url}")
        
        response = requests.get(url, timeout=5)
        print(f"[Currency] Response status: {response.status_code}")
        
        response.raise_for_status()
        
        data = response.json()
        print(f"[Currency] Response data keys: {data.keys()}")
        
        # Frankfurter returns: {"amount": 1.0, "base": "USD", "date": "2024-01-01", "rates": {...}}
        if 'rates' in data and data.get('base') == base_currency:
            rates = {
                'base': base_currency,
                **data['rates']
            }
            _save_cached_rates(rates)
            print(f"[Currency] Successfully fetched {len(rates)-1} rates")
            return rates
        else:
            print(f"[Currency] API response missing 'rates' or 'base' field")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"[Currency] Network error: {e}")
        # Return cached rates even if expired as fallback
        return cached_rates
    except Exception as e:
        print(f"[Currency] Unexpected error: {e}")
        return cached_rates

def convert_currency(
    amount: float, 
    from_currency: str, 
    to_currency: str
) -> Optional[float]:
    """
    Convert amount from one currency to another.
    Returns converted amount or None if conversion fails.
    """
    if from_currency.upper() == to_currency.upper():
        return amount
    
    # Get rates with from_currency as base
    rates = get_exchange_rates(from_currency.upper())
    if not rates:
        print(f"[Currency] No rates available for {from_currency}")
        return None
    
    to_rate = rates.get(to_currency.upper())
    if not to_rate:
        print(f"[Currency] No rate for {to_currency}")
        return None
    
    return amount * to_rate

def format_amount(amount: float, currency: str, show_symbol: bool = True) -> str:
    """
    Format amount with currency symbol.
    Examples: format_amount(1234.56, "USD") -> "$1,234.56"
    """
    symbol = get_currency_symbol(currency) if show_symbol else ""
    
    # Format with commas and 2 decimal places
    formatted = f"{amount:,.2f}"
    
    # Symbol placement (most currencies prefix, some suffix)
    suffix_currencies = ["EUR"]  # Add more as needed
    if currency.upper() in suffix_currencies:
        return f"{formatted} {symbol}"
    else:
        return f"{symbol}{formatted}".replace("$", " $").strip() if symbol else formatted
