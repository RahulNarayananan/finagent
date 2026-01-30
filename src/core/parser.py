from datetime import date, timedelta
from dateutil import parser as date_parser
from typing import List, Optional
from .llm import (
    get_llm, 
    EXTRACTION_PROMPT, 
    MULTI_TRANSACTION_DETECTION_PROMPT,
    MULTI_TRANSACTION_EXTRACTION_PROMPT
)
from .models import Transaction, TransactionCount, MultiTransactionResponse

def normalize_transaction_dates(transaction: Transaction) -> Transaction:
    """Normalize relative dates to ISO format."""
    if transaction.date.lower() == "today":
        transaction.date = date.today().isoformat()
    elif transaction.date.lower() == "yesterday":
        transaction.date = (date.today() - timedelta(days=1)).isoformat()
    else:
        try:
            # Attempt to parse loose date strings
            dt = date_parser.parse(transaction.date)
            transaction.date = dt.date().isoformat()
        except:
            # If parsing fails, fall back to today
            transaction.date = date.today().isoformat()
    return transaction

def detect_multiple_transactions(text: str) -> bool:
    """
    Detects if the input text contains multiple distinct transactions.
    Returns True if multiple transactions are detected.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(TransactionCount)
    
    try:
        chain = MULTI_TRANSACTION_DETECTION_PROMPT | structured_llm
        result = chain.invoke({"text": text})
        return result.has_multiple
    except Exception as e:
        print(f"Error detecting multiple transactions: {e}")
        # Default to single transaction on error
        return False

def parse_multiple_transactions(text: str) -> List[Transaction]:
    """
    Parses text containing multiple transactions into a list of Transaction objects.
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(MultiTransactionResponse)
    
    try:
        chain = MULTI_TRANSACTION_EXTRACTION_PROMPT | structured_llm
        result = chain.invoke({"text": text})
        
        # Normalize dates for all transactions
        normalized_transactions = []
        for transaction in result.transactions:
            normalized_transactions.append(normalize_transaction_dates(transaction))
        
        return normalized_transactions
    except Exception as e:
        print(f"Error parsing multiple transactions: {e}")
        import traceback
        traceback.print_exc()
        return []

def parse_transaction_text(text: str) -> Optional[Transaction | List[Transaction]]:
    """
    Parses unstructured text into Transaction object(s).
    Automatically detects and handles multiple transactions.
    
    Returns:
        - Single Transaction if one transaction detected
        - List[Transaction] if multiple transactions detected
        - None if parsing fails
    """
    # First, check if there are multiple transactions
    if detect_multiple_transactions(text):
        print(f"Detected multiple transactions in input")
        transactions = parse_multiple_transactions(text)
        return transactions if transactions else None
    
    # Single transaction parsing
    llm = get_llm()
    structured_llm = llm.with_structured_output(Transaction)
    
    try:
        chain = EXTRACTION_PROMPT | structured_llm
        transaction = chain.invoke({"text": text})
        
        # Normalize date
        transaction = normalize_transaction_dates(transaction)
        
        return transaction
    except Exception as e:
        print(f"Error parsing transaction: {e}")
        import traceback
        traceback.print_exc()
        return None
